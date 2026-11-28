"""Owner-scoped personal preference state; not business evidence."""
from dataclasses import dataclass
from uuid import UUID

CONSENT_VERSION = "member-memory-v1"
CONSENT_SECONDS = 90 * 86400
MAX_MEMBER_MEMORIES = 20
MAX_PREFERENCE_CHARS = 300


@dataclass(frozen=True, slots=True)
class MemberConsent:
    epoch: UUID
    expires_at: int


@dataclass(frozen=True, slots=True)
class MemberPreference:
    id: UUID
    preference: str
