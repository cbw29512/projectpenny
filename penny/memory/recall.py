"""Read-only bounded retrieval for live internal claims, not member chats."""
import logging
from uuid import UUID

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .review_state import MAX_RECALL_CHARS, MAX_RECALL_RECORDS, ReviewedMemory

logger = logging.getLogger(__name__)


def recall(dsn, task_id: UUID, fence: UUID) -> tuple[ReviewedMemory, ...]:
    try:
        if type(task_id) is not UUID or type(fence) is not UUID:
            return ()
        if not authorize(Actor.WORKER, Capability.RECALL_BUSINESS_MEMORY).allowed:
            return ()
        with locked(dsn) as (conn, control, now):
            if control["paused"]:
                return ()
            task = conn.execute(
                """SELECT id FROM work_task WHERE id=%s AND fence=%s
                   AND state='running' AND member_id IS NULL AND lease_until>%s""",
                (task_id,fence,now),
            ).fetchone()
            if not task:
                return ()
            rows = conn.execute(
                """SELECT source_task_id,kind,content FROM business_memory
                   WHERE revoked_at IS NULL AND expires_at>%s
                   ORDER BY approved_at DESC,source_task_id LIMIT %s""",
                (now,MAX_RECALL_RECORDS),
            ).fetchall()
            result = []
            remaining = MAX_RECALL_CHARS
            for row in rows:
                # Preserve whole records, not misleading clipped statements.
                if len(row["content"]) > remaining:
                    continue
                result.append(ReviewedMemory(row["source_task_id"],row["kind"],row["content"]))
                remaining -= len(row["content"])
            return tuple(result)
    except Exception as exc:
        logger.error("Business memory retrieval failed (%s)", type(exc).__name__)
        raise
