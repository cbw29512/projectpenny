"""Bounded private operator read model. Never exposed as a web endpoint."""
import logging

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.review import _valid_id
from penny.scheduler.storage_db import locked
from .quality import _latest,_verdict
from .quality_state import CRITERIA
from .workshop_intake import read_locked

logger=logging.getLogger(__name__)
MAX_LIST=20


def recent(dsn,*,limit=MAX_LIST):
    try:
        if type(limit) is not int or not 1<=limit<=MAX_LIST:
            raise ValueError("invalid list limit")
        if not authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            rows=conn.execute("""SELECT w.task_id,w.opportunity_id,t.state,t.deadline,
                t.submitted_at, a.content_sha256
                FROM workshop_task w JOIN work_task t ON t.id=w.task_id
                LEFT JOIN workshop_artifact a ON a.task_id=w.task_id
                WHERE t.member_id IS NULL
                ORDER BY t.submitted_at DESC,w.task_id DESC LIMIT %s""",(limit,)).fetchall()
            return [{"task_id":str(row["task_id"]),"opportunity_id":str(row["opportunity_id"]),
                     "task_state":"expired" if row["state"]=="queued" and row["deadline"]<=now
                     else row["state"],"submitted_at":row["submitted_at"],
                     "artifact_recorded":row["content_sha256"] is not None} for row in rows]
    except Exception as exc:
        logger.error("Workshop operator list failed (%s)",type(exc).__name__)
        raise


def inspect(dsn,task_id):
    """Show exact review ID, digest and content together under one lock."""
    try:
        if not _valid_id(task_id):
            raise ValueError("invalid task identifier")
        if not authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            artifact=read_locked(conn,task_id,now)
            if artifact is None:
                return None
            row=_latest(conn,task_id)
            state=_verdict(row)
            data=artifact["artifact"]
            if artifact["status"]!="private_prototype" or (row and
                    data["content_sha256"]!=row["content_sha256"]):
                state="unavailable"
            return {"task_id":str(task_id),"artifact":data,"artifact_status":artifact["status"],
                    "quality_status":state,"review_id":str(row["id"]) if row else None,
                    "reviewed_digest":row["content_sha256"] if row else None,
                    "checks":{k:row[k] for k in CRITERIA} if row else None,
                    "private_export_ready":state=="passed",
                    "commercial_release_authorized":False}
    except Exception as exc:
        logger.error("Workshop operator inspection failed (%s)",type(exc).__name__)
        raise
