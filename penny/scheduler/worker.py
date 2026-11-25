"""One-shot worker: no background loop or external side effects."""
import logging
import time
from enum import Enum

from .outcomes import complete

logger = logging.getLogger(__name__)


class WorkerResult(str, Enum):
    IDLE = "idle"
    COMPLETED = "completed"
    BLOCKED = "blocked"


def run_once(store, brain, *, finish=complete, clock=time.time) -> WorkerResult:
    """Trusted internal entry point; output is a draft, not a public reply."""
    try:
        claim = store.claim()
        if claim is None:
            return WorkerResult.IDLE
        budget = min(90.0, claim.lease_until - clock() - 5.0)
        if budget <= 0:
            logger.warning("Worker claim has insufficient execution budget")
            return WorkerResult.BLOCKED
        text = brain.generate(claim.payload, budget)
        if not isinstance(text, str) or not text.strip() or len(text) > 16000 or "\x00" in text:
            raise ValueError("invalid inference result")
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
