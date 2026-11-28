"""Typed candidate state. Model output cannot set trust or ownership."""
from dataclasses import dataclass
from enum import Enum


class MemoryKind(str, Enum):
    LESSON = "lesson"
    FAILURE = "failure"
    IDEA = "idea"
    SKILL = "skill"
    MILESTONE = "milestone"


@dataclass(frozen=True, slots=True)
class Candidate:
    kind: MemoryKind
    content: str


REVIEW_PREFIX = "memory-review:"
MAX_CONTENT = 1000
