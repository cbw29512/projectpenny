"""Pure admission and selection; callers must hold a transactional lock."""

import logging
from fractions import Fraction

from .state import Admission, QueueClass, QueueSnapshot, TaskSpec, Tier

logger = logging.getLogger(__name__)
WAITING_CAP = 10
CLASS_CAP = {QueueClass.FREE: 3, QueueClass.SUPPORTER: 5, QueueClass.BUSINESS: 2}
SHARE = {QueueClass.BUSINESS: 60, QueueClass.SUPPORTER: 30, QueueClass.FREE: 10}
MEMBER_CAP = {
    Tier.FREE: 1, Tier.COPPER: 1, Tier.BRONZE: 1,
    Tier.SILVER: 2, Tier.GOLD: 2, Tier.PLATINUM: 3, Tier.INNER_CIRCLE: 3,
}
AGE_SECONDS = 900  # Provisional; adjust only after benchmark.


def _validate_snapshot(state: QueueSnapshot, now: int) -> None:
    # Fail closed on corrupted state rather than dispatch another worker.
    if type(now) is not int or now < 0:
        raise ValueError("invalid scheduler clock")
    records = state.waiting + ((state.active,) if state.active else ())
    if any(not item.valid() or item.submitted_at > now for item in records):
        raise ValueError("invalid persisted task")
    if len({item.task_id for item in records}) != len(records):
        raise ValueError("duplicate persisted task ID")
    if any(type(state.usage(c)) is not int or state.usage(c) < 0 for c in SHARE):
        raise ValueError("invalid measured compute usage")


def admission(state: QueueSnapshot, task: TaskSpec, now: int) -> Admission:
    """Return a decision, not a reservation. Never invoke an LLM here."""
    try:
        _validate_snapshot(state, now)
        if not task.valid() or task.submitted_at > now:
            return Admission.INVALID
        if state.paused:
            return Admission.PAUSED
        if task.expires_at <= now:
            return Admission.EXPIRED
        records = state.waiting + ((state.active,) if state.active else ())
        if any(item.task_id == task.task_id for item in records):
            return Admission.DUPLICATE_ID
        # Expired rows still occupy physical slots until the adapter removes
        # them in the same transaction; never exceed the stored waiting cap.
        if len(state.waiting) >= WAITING_CAP or sum(
            item.queue_class == task.queue_class for item in state.waiting
        ) >= CLASS_CAP[task.queue_class]:
            return Admission.FULL
        if task.member_id is not None:
            outstanding = sum(item.member_id == task.member_id for item in records)
            if outstanding >= MEMBER_CAP[task.tier]:
                return Admission.MEMBER_LIMIT
        return Admission.ACCEPT
    except (TypeError, ValueError, AttributeError, KeyError):
        logger.warning("Scheduler rejected invalid admission state", exc_info=True)
        return Admission.INVALID


def _arrival(task: TaskSpec) -> tuple[int, str]:
    return task.submitted_at, task.task_id


def next_task(state: QueueSnapshot, now: int) -> TaskSpec | None:
    """Return a candidate only; claim and entitlement recheck belong to storage."""
    try:
        _validate_snapshot(state, now)
        # Incoming work never interrupts an existing task, even if higher tier.
        if state.paused or state.active is not None:
            return None
        candidates = [item for item in state.waiting if item.expires_at > now]
        if not candidates:
            return None
        # Age override ensures priority cannot indefinitely hide older work.
        aged = [item for item in candidates if now - item.submitted_at >= AGE_SECONDS]
        if aged:
            return min(aged, key=_arrival)
        if state.last_member_id is not None:
            alternatives = [item for item in candidates if item.member_id != state.last_member_id]
            if alternatives:
                candidates = alternatives
        # Normalize actual compute time by target share; idle classes don't
        # block others. Fraction avoids floating-point tie instability.
        available = {item.queue_class for item in candidates}
        chosen_class = min(
            available,
            key=lambda c: (Fraction(state.usage(c), SHARE[c]), -SHARE[c]),
        )
        eligible = [item for item in candidates if item.queue_class == chosen_class]
        return min(eligible, key=lambda item: (-int(item.tier or 0), *_arrival(item)))
    except (TypeError, ValueError, AttributeError, KeyError):
        logger.error("Scheduler refused invalid dispatch state", exc_info=True)
        return None
