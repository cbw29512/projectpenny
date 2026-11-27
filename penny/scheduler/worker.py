"""One-shot worker: no background loop or external side effects."""
import logging
import time
from enum import Enum

from penny.guardian.policy import authorize, validate_draft
from penny.guardian.state import Actor, Capability

from penny.memory.recall import recall
from penny.memory.member_recall import recall_preferences

from .outcomes import complete

logger = logging.getLogger(__name__)


class WorkerResult(str, Enum):
    IDLE = "idle"
    COMPLETED = "completed"
    BLOCKED = "blocked"


def run_once(store, brain, *, finish=complete, clock=time.time, personal_recall=None) -> WorkerResult:
    """Trusted internal entry point; output is a draft, not a public reply."""
    try:
        permission = authorize(Actor.WORKER, Capability.GENERATE_DRAFT)
        if not permission.allowed:
            logger.warning("Guardian blocked generation: %s", permission.reason)
            return WorkerResult.BLOCKED
        claim = store.claim()
        if claim is None:
            return WorkerResult.IDLE
        budget = min(90.0, claim.lease_until - clock() - 5.0)
        if budget <= 0:
            logger.warning("Worker claim has insufficient execution budget")
            return WorkerResult.BLOCKED
        if claim.memory_enabled and claim.personal_memory_enabled:
            return WorkerResult.BLOCKED
        if claim.personal_memory_enabled:
            reader=recall_preferences if personal_recall is None else personal_recall
            preferences = reader(store.dsn,claim.task_id,claim.fence)
            budget = min(90.0,claim.lease_until-clock()-5.0)
            if budget <= 0:
                return WorkerResult.BLOCKED
            text = (brain.generate_with_preferences(claim.payload,budget,preferences)
                    if preferences else brain.generate(claim.payload,budget))
        elif claim.memory_enabled:
            memories = recall(store.dsn, claim.task_id, claim.fence)
            # Recall takes time too; never give inference the old lease budget.
            budget = min(90.0, claim.lease_until - clock() - 5.0)
            if budget <= 0:
                return WorkerResult.BLOCKED
            if memories:
                text = brain.generate_with_memory(claim.payload, budget, memories)
            else:
                text = brain.generate(claim.payload, budget)
        else:
            text = brain.generate(claim.payload, budget)
        decision = validate_draft(text)
        if not decision.allowed:
            logger.warning("Guardian blocked draft storage: %s", decision.reason)
            return WorkerResult.BLOCKED
        if clock() >= claim.lease_until:
            logger.warning("Worker result arrived after lease")
            return WorkerResult.BLOCKED
        # Storage atomically checks the fence and lease again using DB time.
        if not finish(store.dsn, claim.task_id, claim.fence, success=True, result=text):
            logger.warning("Worker could not commit fenced result")
            return WorkerResult.BLOCKED
        return WorkerResult.COMPLETED
    except Exception as exc:
        # Do not release a claim after ambiguous transport or storage failure.
        logger.error("Worker stopped (%s); review claim before recovery", type(exc).__name__)
        return WorkerResult.BLOCKED
