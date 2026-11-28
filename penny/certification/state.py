"""Immutable evidence and reviewer state for personality regression."""
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

SUITE_VERSION = "penny-personality-v3"
REPEATS = 2
MAX_RESPONSE_CHARS = 16000


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    prompt: str
    criteria: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModelManifest:
    # Operator-supplied model and exact runtime configuration fingerprints.
    model_digest: str
    config_digest: str


@dataclass(frozen=True, slots=True)
class Observation:
    case_id: str
    repeat: int
    response: str


@dataclass(frozen=True, slots=True)
class EvidenceRun:
    model: ModelManifest
    identity_digest: str
    suite_digest: str
    observations: tuple[Observation, ...]


@dataclass(frozen=True, slots=True)
class CaseReview:
    case_id: str
    repeat: int
    criterion_verdicts: tuple[Verdict, ...]
    notes: str


@dataclass(frozen=True, slots=True)
class Review:
    reviewer_id: UUID
    evidence_digest: str
    cases: tuple[CaseReview, ...]
