"""Fenced private artifact storage and trusted plain-text retrieval."""
import logging
from hashlib import sha256

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.review import _valid_id
from penny.scheduler.storage_db import locked
from .checklist import render_checklist
from .store import LATEST
from .workshop_state import PREFIX,FORMAT

logger=logging.getLogger(__name__)


def stage_artifact(conn,row,raw,now):
    try:
        if row["member_id"] is not None or not row["idempotency_key"].startswith(PREFIX):
            return False
        link=conn.execute("SELECT opportunity_id FROM workshop_task WHERE task_id=%s",
                          (row["id"],)).fetchone()
        if link is None:
            logger.warning("Workshop staging refused: missing task link")
            return False
        if not authorize(Actor.WORKER,Capability.STAGE_WORKSHOP).allowed:
            logger.warning("Workshop staging refused: Guardian denied")
            return False
        experiment=conn.execute(LATEST+" WHERE o.id=%s",(link["opportunity_id"],)).fetchone()
        if experiment is None or experiment["action"]!="started" or experiment["deadline"]<=now:
            logger.warning("Workshop staging refused: experiment unavailable")
            return False
        if conn.execute("SELECT paused FROM scheduler_control WHERE singleton").fetchone()["paused"]:
            logger.warning("Workshop staging refused: scheduler paused")
            return False
        content=render_checklist(raw)
        if content is None:
            logger.warning("Workshop staging refused: checklist validation")
            return False
        conn.execute("INSERT INTO workshop_artifact VALUES (%s,%s,%s,%s,%s,%s)",
            (row["id"],FORMAT,content,sha256(content.encode("utf-8")).hexdigest(),
             sha256(raw.encode("utf-8")).hexdigest(),now))
        return True
    except Exception as exc:
        logger.error("Workshop artifact intake failed (%s)",type(exc).__name__)
        raise


def read_locked(conn,task_id,now):
    """Trusted internal helper; caller holds scheduler lock."""
    row=conn.execute("""SELECT t.state,t.deadline,a.format_version,a.content,
        a.content_sha256,a.result_sha256,o.result,o.status AS outcome_status
        FROM workshop_task w JOIN work_task t ON t.id=w.task_id
        LEFT JOIN workshop_artifact a ON a.task_id=w.task_id
        LEFT JOIN task_outcome o ON o.task_id=w.task_id
        WHERE w.task_id=%s AND t.member_id IS NULL""",(task_id,)).fetchone()
    if row is None:
        return None
    state=row["state"]
    if state=="queued" and row["deadline"]<=now:
        state="expired"
    artifact=None
    if state=="succeeded":
        state="not_staged"
        if row["content"] is not None:
            if (row["outcome_status"]!="succeeded" or row["result"] is None
                    or sha256(row["result"].encode("utf-8")).hexdigest()!=row["result_sha256"]
                    or sha256(row["content"].encode("utf-8")).hexdigest()!=row["content_sha256"]
                    or render_checklist(row["result"])!=row["content"]):
                return {"status":"integrity_error","artifact":None}
            state="private_prototype"
            artifact={k:row[k] for k in ("format_version","content","content_sha256")}
    return {"status":state,"artifact":artifact}


def read_artifact(dsn,task_id):
    """Only trusted admin; render as text/plain, never executable markup."""
    try:
        if not _valid_id(task_id):
            raise ValueError("invalid prototype identifier")
        if not authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            return read_locked(conn,task_id,now)
    except Exception as exc:
        logger.error("Workshop artifact read failed (%s)",type(exc).__name__)
        raise


def cancel_queued(conn,opportunity_id,now):
    # Called under scheduler lock when experiment closes. Running inference
    # cannot be killed here; fenced completion will refuse artifact staging.
    conn.execute("""WITH canceled AS (
        UPDATE work_task SET state='canceled' WHERE state='queued'
        AND id IN (SELECT task_id FROM workshop_task WHERE opportunity_id=%s)
        RETURNING id)
        INSERT INTO task_outcome SELECT id,'canceled','experiment closed',%s,0 FROM canceled""",
        (opportunity_id,now))
