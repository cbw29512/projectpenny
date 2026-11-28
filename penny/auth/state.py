"""Session state. Never serialize secrets into logs."""
from dataclasses import dataclass, field
from uuid import UUID

SESSION_SECONDS = 3600
MAX_ACTIVE_SESSIONS = 5


@dataclass(frozen=True, slots=True)
class IssuedSession:
    id: UUID
    token: str = field(repr=False)
    expires_at: int
