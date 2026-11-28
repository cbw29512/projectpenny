"""Bounded maintenance proposal vocabulary, separate from approved memory."""
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from .task import INFORMED_PREFIX

MAINTENANCE_PREFIX = INFORMED_PREFIX + "maintenance-"
MAX_TOPIC_CHARS = 1000
MAINTENANCE_PROMPT = (
    "Review supplied historical memories for the topic below. Return one JSON object "
    'with action (correct, consolidate, outdated, contradiction), sources (list of '
    'recalled source UUIDs), rationale (max 500 chars), replacement (max 1000 chars '
    'for correct/consolidate, null otherwise). Correct/outdated use one source; '
    'consolidate/contradiction use two or three distinct sources. '
    'Return {} if insufficient evidence. Do not claim verification. Topic: '
)


class MaintenanceAction(str, Enum):
    CORRECT = "correct"
    CONSOLIDATE = "consolidate"
    OUTDATED = "outdated"
    CONTRADICTION = "contradiction"


@dataclass(frozen=True, slots=True)
class MaintenanceProposal:
    action: MaintenanceAction
    sources: tuple[UUID, ...]
    rationale: str
    replacement: str | None
