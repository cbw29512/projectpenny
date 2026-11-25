"""Business memory state and conservative initial retention limits."""
from dataclasses import dataclass
from uuid import UUID

MAX_RETENTION_SECONDS = 365 * 86400
MAX_RECALL_RECORDS = 3
MAX_RECALL_CHARS = 1500


@dataclass(frozen=True, slots=True)
class ReviewedMemory:
    source_task_id: UUID
    kind: str
    content: str
