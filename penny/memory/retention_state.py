"""Provisional private draft retention contract; approved history is out of scope."""
from dataclasses import dataclass
from uuid import UUID

MAX_PURGE_BATCH = 25
REDACTED = "[expired private draft redacted]"


@dataclass(frozen=True, slots=True)
class PurgeResult:
    task_ids: tuple[UUID, ...] = ()
