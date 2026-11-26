"""Explicit administrator-only bounded logical redaction of expired private drafts."""
import logging

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .maintenance_state import MAINTENANCE_PREFIX
from .review import _valid_id, _valid_ref
from .retention_state import MAX_PURGE_BATCH, REDACTED, PurgeResult
from .state import REVIEW_PREFIX

logger = logging.getLogger(__name__)


def purge_expired(dsn, *, reviewer_id, review_ref, limit=MAX_PURGE_BATCH):
    """Internal trusted admin adapter only; requires authenticated caller.

    Never purge approved history, decided proposals, public jobs or running jobs.
    Redacts live database draft text, not backups, WAL or downstream copies.
    """
    try:
        decision = authorize(Actor.ADMIN,Capability.PURGE_EXPIRED_MEMORY_DRAFTS)
        if not decision.allowed:
            return PurgeResult()
        if not _valid_id(reviewer_id) or not _valid_ref(review_ref):
            raise ValueError("invalid purge authorization reference")
        if type(limit) is not int or not 1 <= limit <= MAX_PURGE_BATCH:
            raise ValueError("invalid purge batch")
        with locked(dsn) as (conn,_,now):
            # Do not interpolate untrusted identifiers or allow caller-selected SQL.
            rows = conn.execute(
                """WITH due AS (
                   SELECT c.source_task_id AS task_id,'candidate' AS kind,c.review_until
                   FROM memory_candidate c JOIN work_task t ON t.id=c.source_task_id
                   JOIN task_outcome o ON o.task_id=t.id
                   WHERE c.purged_at IS NULL AND c.review_until<=to_timestamp(%s)
                   AND t.member_id IS NULL AND t.state='succeeded' AND o.status='succeeded'
                   AND left(t.idempotency_key,length(%s))=%s
                   AND NOT EXISTS (SELECT 1 FROM business_memory m WHERE m.source_task_id=c.source_task_id)
                   UNION ALL
                   SELECT p.task_id,'maintenance',p.review_until
                   FROM memory_maintenance_proposal p JOIN work_task t ON t.id=p.task_id
                   JOIN task_outcome o ON o.task_id=t.id
                   WHERE p.purged_at IS NULL AND p.review_until<=to_timestamp(%s)
                   AND t.member_id IS NULL AND t.state='succeeded' AND o.status='succeeded'
                   AND left(t.idempotency_key,length(%s))=%s
                   AND NOT EXISTS (SELECT 1 FROM memory_maintenance_decision d WHERE d.task_id=p.task_id)
                   ) SELECT task_id,kind FROM due ORDER BY review_until,task_id LIMIT %s""",
                (now,REVIEW_PREFIX,REVIEW_PREFIX,now,MAINTENANCE_PREFIX,MAINTENANCE_PREFIX,limit),
            ).fetchall()
            for row in rows:
                task = row["task_id"]
                if row["kind"] == "candidate":
                    conn.execute(
                        "UPDATE memory_candidate SET content=%s,purged_at=to_timestamp(%s) WHERE source_task_id=%s",
                        (REDACTED,now,task),
                    )
                else:
                    # Preserve NULL for actions that never had a replacement.
                    conn.execute(
                        """UPDATE memory_maintenance_proposal SET rationale=%s,
                           replacement=CASE WHEN replacement IS NULL THEN NULL ELSE %s END,
                           purged_at=to_timestamp(%s) WHERE task_id=%s""",
                        (REDACTED,REDACTED,now,task),
                    )
                conn.execute("UPDATE work_task SET payload=%s WHERE id=%s",(REDACTED,task))
                conn.execute("UPDATE task_outcome SET result=%s WHERE task_id=%s",(REDACTED,task))
                conn.execute(
                    "INSERT INTO memory_draft_purge_event VALUES (%s,%s,%s,%s,%s,%s)",
                    (task,row["kind"],reviewer_id,review_ref,now,decision.policy_version),
                )
            return PurgeResult(tuple(row["task_id"] for row in rows))
    except Exception as exc:
        logger.error("Expired memory draft purge failed (%s)",type(exc).__name__)
        raise
