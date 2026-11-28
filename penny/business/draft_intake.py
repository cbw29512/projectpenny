"""Quarantine a model draft atomically with the fenced scheduler outcome."""
import logging
from hashlib import sha256

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.review import _valid_id
from penny.scheduler.storage_db import locked
from .draft_state import DRAFT_PREFIX
from .draft_parse import parse_draft

logger=logging.getLogger(__name__)


def stage_from_draft(conn,row,raw):
    try:
        if row["member_id"] is not None or not row["idempotency_key"].startswith(DRAFT_PREFIX):
            return False
        if not conn.execute("SELECT 1 FROM business_draft_task WHERE task_id=%s",(row["id"],)).fetchone():
            return False
        if not authorize(Actor.WORKER,Capability.STAGE_BUSINESS_DRAFT).allowed:
            return False
        draft=parse_draft(raw)
        if draft is None:
            return False
        conn.execute("""INSERT INTO business_draft_candidate VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (row["id"],draft.category.value,draft.title,draft.hypothesis,draft.metric.value,
             draft.target,draft.duration_seconds,draft.additional_cash_cents,
             sha256(raw.encode("utf-8")).hexdigest()))
        return True
    except Exception as exc:
        logger.error("Business draft intake failed (%s)",type(exc).__name__)
        raise


def draft_status(dsn,task_id):
    """Private trusted admin adapter only; no public or member access."""
    try:
        if not _valid_id(task_id):
            raise ValueError("invalid draft task")
        if not authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            row=conn.execute("""SELECT t.state,t.deadline,c.category,c.title,c.hypothesis,
                c.metric,c.target,c.duration_seconds,c.additional_cash_cents,c.result_sha256,
                p.opportunity_id
                FROM business_draft_task d JOIN work_task t ON t.id=d.task_id
                LEFT JOIN business_draft_candidate c ON c.task_id=d.task_id
                LEFT JOIN business_draft_promotion p ON p.task_id=d.task_id
                WHERE d.task_id=%s AND t.member_id IS NULL""",(task_id,)).fetchone()
            if row is None:
                return None
            state=row["state"]
            if state=="queued" and row["deadline"]<=now:
                state="expired"
            if state=="succeeded":
                state="quarantined" if row["result_sha256"] else "invalid_draft"
            candidate=None
            if state=="quarantined":
                candidate={k:row[k] for k in ("category","title","hypothesis","metric","target",
                    "duration_seconds","additional_cash_cents","result_sha256")}
            result={"status":state,"candidate":candidate,"authorized_cents":0}
            if row["opportunity_id"] is not None:
                result.update(status="promoted",opportunity_id=row["opportunity_id"])
            return result
    except Exception as exc:
        logger.error("Business draft status unavailable (%s)",type(exc).__name__)
        raise
