"""Internal administrator-only adjudication of exact maintenance proposals."""
import logging

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .adjudication_db import apply_changes
from .adjudication_state import ReviewChoice
from .evidence import fingerprint
from .maintenance_parse import parse_maintenance
from .maintenance_state import MaintenanceAction
from .review import _valid_id, _valid_ref
from .review_state import MAX_RETENTION_SECONDS

logger = logging.getLogger(__name__)


def adjudicate(dsn, task_id, *, reviewer_id, review_ref, evidence, expected_proposal,
               choice, retention_seconds=0):
    """Caller must authenticate administrator and independently review evidence.

    Exact structured proposal and source set must match the reviewed snapshot.
    A contradiction can be acknowledged, never automatically resolved.
    """
    try:
        decision = authorize(Actor.ADMIN,Capability.REVIEW_MEMORY_MAINTENANCE)
        if not decision.allowed:
            return False
        if not _valid_id(task_id) or not _valid_id(reviewer_id) or not _valid_ref(review_ref):
            raise ValueError("invalid review identity")
        if type(choice) is not ReviewChoice:
            raise ValueError("invalid review choice")
        proposal = parse_maintenance(expected_proposal)
        if proposal is None:
            raise ValueError("invalid reviewed proposal")
        replacement = (choice is ReviewChoice.APPLY and proposal.action in
                       (MaintenanceAction.CORRECT,MaintenanceAction.CONSOLIDATE))
        if type(retention_seconds) is not int or (
            replacement and not 1 <= retention_seconds <= MAX_RETENTION_SECONDS
        ) or (not replacement and retention_seconds != 0):
            raise ValueError("invalid retention")
        if choice is ReviewChoice.APPLY and proposal.action is MaintenanceAction.CONTRADICTION:
            return False
        if choice is ReviewChoice.ACKNOWLEDGE and proposal.action is not MaintenanceAction.CONTRADICTION:
            return False
        mark = fingerprint(task_id,evidence)
        with locked(dsn) as (conn,_,now):
            row = conn.execute(
                """SELECT p.action,p.rationale,p.replacement FROM memory_maintenance_proposal p
                   JOIN work_task t ON t.id=p.task_id JOIN task_outcome o ON o.task_id=t.id
                   WHERE p.task_id=%s AND t.member_id IS NULL AND o.status='succeeded'
                   AND NOT EXISTS (SELECT 1 FROM memory_maintenance_decision d WHERE d.task_id=p.task_id)""",
                (task_id,),
            ).fetchone()
            if not row or (row["action"],row["rationale"],row["replacement"]) != (
                proposal.action.value,proposal.rationale,proposal.replacement):
                return False
            rows = conn.execute(
                """SELECT m.source_task_id,m.kind,m.expires_at,m.revoked_at
                   FROM memory_maintenance_source s JOIN business_memory m
                   ON m.source_task_id=s.source_task_id WHERE s.task_id=%s""",
                (task_id,),
            ).fetchall()
            if {r["source_task_id"] for r in rows} != set(proposal.sources):
                return False
            replacement_id = None
            if choice is ReviewChoice.APPLY:
                if any(r["revoked_at"] is not None or r["expires_at"]<=now for r in rows):
                    return False
                if replacement and len({r["kind"] for r in rows}) != 1:
                    return False
                replacement_id = apply_changes(conn,task_id,proposal,rows,reviewer_id,review_ref,
                                               mark,now,retention_seconds,decision.policy_version)
            verdict = {ReviewChoice.APPLY:"applied",ReviewChoice.REJECT:"rejected",
                       ReviewChoice.ACKNOWLEDGE:"acknowledged"}[choice]
            conn.execute(
                """INSERT INTO memory_maintenance_decision
                   (task_id,verdict,reviewer_id,review_ref,evidence_sha256,evidence_size,
                    decided_at,policy_version,replacement_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (task_id,verdict,reviewer_id,review_ref,mark.digest,mark.byte_count,
                 now,decision.policy_version,replacement_id),
            )
            return True
    except Exception as exc:
        logger.error("Memory maintenance adjudication failed (%s)",type(exc).__name__)
        raise
