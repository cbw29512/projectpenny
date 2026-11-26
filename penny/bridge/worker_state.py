"""Typed one-cycle work selection; no model, network or secret fields."""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Action:
    kind: str
    question_id: UUID | None = None
    fence: UUID | None = None
    task_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Cycle:
    status: str
    retry_after: int = 60
