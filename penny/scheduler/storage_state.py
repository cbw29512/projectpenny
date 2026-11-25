"""Typed return values for the trusted durable repository."""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Receipt:
    status: str
    task_id: UUID | None = None
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class Claim:
    task_id: UUID
    fence: UUID
    payload: str
    lease_until: int
    memory_enabled: bool = False
