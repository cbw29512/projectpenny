"""Recognition state is independent of payment, model memory and entitlements."""
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

CONSENT_VERSION = "recognition-private-v1"
MAX_REQUESTS = 100


class Outcome(str, Enum):
    IMPROVED = "improved"
    UNSUCCESSFUL = "unsuccessful"
    INCONCLUSIVE = "inconclusive"


class Role(str, Enum):
    IDEA = "idea"
    TESTING = "testing"
    BUG_REPORT = "bug_report"
    ADVICE = "advice"


@dataclass(frozen=True, slots=True)
class Recognition:
    request_id: UUID
    outcome_id: UUID
    role: Role
    verdict: Outcome
    message: str
