"""Explicit linkage of reviewed Workshop outcomes to private recognition."""
import logging
from uuid import uuid4
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.review import _valid_id
from penny.scheduler.storage_db import locked
from penny.business.revision_review import status_locked
from penny.business.revision_sources import stored_sources,eligible_sources

logger=logging.getLogger(__name__)
PREFIX="workshop-revision:"


def record_workshop_outcome(dsn,task_id,*,reviewer_id,confirmed):
    try:
        decision=authorize(Actor.ADMIN,Capability.VERIFY_CONTRIBUTION)
        if not decision.allowed:
            return None
        if confirmed is not True or not _valid_id(task_id) or not _valid_id(reviewer_id):
            raise ValueError("invalid outcome confirmation")
        with locked(dsn) as (conn,_,now):
            state=status_locked(conn,task_id,now)
            if not state or not state["improvement_verified"]:
                return None
            sources=stored_sources(conn,task_id)
            if not sources or not eligible_sources(conn,sources,now):
                return None
            prior=conn.execute("SELECT outcome_id FROM workshop_contribution_outcome WHERE task_id=%s",
                               (task_id,)).fetchone()
            if prior:
                return prior["outcome_id"]
            review=conn.execute("SELECT * FROM workshop_revision_review WHERE task_id=%s",
                                (task_id,)).fetchone()
            key=uuid4()
            conn.execute("INSERT INTO contribution_outcome VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (key,PREFIX+str(task_id),"improved",review["evidence_sha256"],
                 review["evidence_size"],reviewer_id,now,decision.policy_version))
            conn.execute("INSERT INTO workshop_contribution_outcome VALUES (%s,%s)",(key,task_id))
            return key
    except Exception as exc:
        logger.error("Workshop recognition outcome refused (%s)",type(exc).__name__)
        raise


def credit_allowed_locked(conn,outcome_id,owner,role,now):
    """Generic outcomes unchanged; Workshop credit needs current reviewed source."""
    outcome=conn.execute("""SELECT o.outcome_ref,w.task_id FROM contribution_outcome o
        LEFT JOIN workshop_contribution_outcome w ON w.outcome_id=o.id WHERE o.id=%s""",
        (outcome_id,)).fetchone()
    if not outcome:
        return False
    if not outcome["outcome_ref"].startswith(PREFIX):
        return outcome["task_id"] is None
    task=outcome["task_id"]
    if task is None or role!="idea":
        return False
    state=status_locked(conn,task,now)
    if not state or not state["improvement_verified"]:
        return False
    sources=stored_sources(conn,task)
    if not sources or not eligible_sources(conn,sources,now):
        return False
    return conn.execute("""SELECT 1 FROM workshop_revision_suggestion w
        JOIN community_suggestion s ON s.id=w.suggestion_id
        WHERE w.task_id=%s AND s.member_id=%s LIMIT 1""",(task,owner)).fetchone() is not None
