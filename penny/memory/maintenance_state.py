"""Bounded maintenance proposal vocabulary, separate from approved memory."""
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from .task import INFORMED_PREFIX

MAINTENANCE_PREFIX = INFORMED_PREFIX + "maintenance-"


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
