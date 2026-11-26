"""Bounded, relevance-ranked recall for explicitly authorized internal claims."""
import logging
from uuid import UUID, uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .ranking import task_search_expression, select_ranked
from .review_state import MAX_RANKED_CANDIDATES, RECALL_RANK_VERSION, ReviewedMemory
from .task import INFORMED_PREFIX

logger = logging.getLogger(__name__)


def recall(dsn, task_id: UUID, fence: UUID) -> tuple[ReviewedMemory, ...]:
    try:
        if type(task_id) is not UUID or type(fence) is not UUID:
            return ()
        decision = authorize(Actor.WORKER, Capability.RECALL_BUSINESS_MEMORY)
        if not decision.allowed:
            return ()
        with locked(dsn) as (conn, control, now):
            if control["paused"]:
                return ()
            task = conn.execute(
                """SELECT payload,idempotency_key FROM work_task
                   WHERE id=%s AND fence=%s AND state='running'
                   AND member_id IS NULL AND lease_until>%s""",
                (task_id,fence,now),
            ).fetchone()
            if not task or not task["idempotency_key"].startswith(INFORMED_PREFIX):
                return ()
            # Use trusted stored task text, not a second caller-supplied query.
            query = task_search_expression(task["idempotency_key"], task["payload"])
            rows = conn.execute(
                """WITH q AS (
                       SELECT websearch_to_tsquery('english',%s) AS terms
                   )
                   SELECT source_task_id,kind,content,
                          ts_rank(to_tsvector('english',content),q.terms) AS relevance
                   FROM business_memory CROSS JOIN q
                   WHERE revoked_at IS NULL AND expires_at>%s
                   AND to_tsvector('english',content) @@ q.terms
                   ORDER BY relevance DESC,approved_at DESC,source_task_id LIMIT %s""",
                (query,now,MAX_RANKED_CANDIDATES),
            ).fetchall() if query else []
            selected = select_ranked(rows)
            event_id = uuid4()
            conn.execute(
                """INSERT INTO memory_recall_event
                   (id,task_id,fence,recorded_at,policy_version,rank_version,selected_count)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (event_id,task_id,fence,now,decision.policy_version,
                 RECALL_RANK_VERSION,len(selected)),
            )
            for position, record in enumerate(selected,1):
                conn.execute(
                    "INSERT INTO memory_recall_source VALUES (%s,%s,%s)",
                    (event_id,record.source_task_id,position),
                )
            # Transaction commits before any selected record is returned.
            return selected
    except Exception as exc:
        logger.error("Business memory retrieval failed (%s)", type(exc).__name__)
        raise
