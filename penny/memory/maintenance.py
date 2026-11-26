"""Explicit internal maintenance review and fenced, quarantined proposal storage."""
import logging
import re

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from .maintenance_parse import parse_maintenance
from .maintenance_state import MAINTENANCE_PREFIX

logger = logging.getLogger(__name__)


def submit_maintenance(store, key: str, topic: str):
    """Trusted scheduler adapter only; no automatic submission or extra model calls."""
    try:
        if type(key) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", key):
            raise ValueError("invalid maintenance key")
        if type(topic) is not str or not topic.strip() or len(topic) > 1000 or "\x00" in topic:
            raise ValueError("invalid maintenance topic")
        prompt = (
            "Review supplied historical memories for the topic below. Return one JSON object "
            'with action (correct, consolidate, outdated, contradiction), sources (list of '
            'recalled source UUIDs), rationale (max 500 chars), replacement (max 1000 chars '
            'for correct/consolidate, null otherwise). Correct/outdated use one source; '
            'consolidate/contradiction use two or three distinct sources. '
            'Return {} if insufficient evidence. Do not claim verification. Topic: ' + topic
        )
        return store.submit(None,MAINTENANCE_PREFIX+key,prompt)
    except Exception as exc:
        logger.warning("Memory maintenance submission rejected (%s)",type(exc).__name__)
        raise


def stage_maintenance(conn, row, raw, now):
    """Only successful fenced internal tasks can stage a proposal."""
    try:
        if row["member_id"] is not None or not row["idempotency_key"].startswith(MAINTENANCE_PREFIX):
            return False
        decision = authorize(Actor.WORKER,Capability.STAGE_MEMORY_MAINTENANCE)
        if not decision.allowed:
            return False
        proposal = parse_maintenance(raw)
        if proposal is None:
            return False
        # All referenced records must come from a single recall event under this
        # execution fence, and still be active at the completion transaction.
        events = conn.execute(
            """SELECT s.event_id,s.source_task_id
               FROM memory_recall_source s
               JOIN memory_recall_event e ON e.id=s.event_id
               JOIN business_memory m ON m.source_task_id=s.source_task_id
               WHERE e.task_id=%s AND e.fence=%s
               AND m.revoked_at IS NULL AND m.expires_at>%s""",
            (row["id"],row["fence"],now),
        ).fetchall()
        by_event = {}
        for event in events:
            by_event.setdefault(event["event_id"],set()).add(event["source_task_id"])
        if not any(set(proposal.sources).issubset(ids) for ids in by_event.values()):
            return False
        conn.execute(
            """INSERT INTO memory_maintenance_proposal
               (task_id,action,rationale,replacement,created_at,policy_version)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (row["id"],proposal.action.value,proposal.rationale,proposal.replacement,
             now,decision.policy_version),
        )
        for source in proposal.sources:
            conn.execute("INSERT INTO memory_maintenance_source VALUES (%s,%s)",
                         (row["id"],source))
        return True
    except Exception as exc:
        logger.error("Memory maintenance staging failed (%s)",type(exc).__name__)
        raise
