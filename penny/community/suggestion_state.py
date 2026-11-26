"""Bounded private suggestion schema and cheap shape screening."""
from dataclasses import dataclass
from enum import Enum
import hashlib
import logging
import re
import unicodedata
from uuid import UUID

logger = logging.getLogger(__name__)
MAX_BODY = 500
OWNER_DAILY = 3
OWNER_PENDING = 3
GLOBAL_DAILY = 60
GLOBAL_PENDING = 100
MAX_RECORDS = 4096


class Verdict(str, Enum):
    ELIGIBLE = "eligible"
    REJECTED = "rejected"
    DEFERRED = "deferred"


REASONS = {
    Verdict.ELIGIBLE: frozenset({"mission_fit"}),
    Verdict.REJECTED: frozenset({"off_topic", "unsafe", "spam"}),
    Verdict.DEFERRED: frozenset({"not_feasible", "needs_research"}),
}


@dataclass(frozen=True, slots=True)
class SuggestionReceipt:
    status: str
    suggestion_id: UUID | None = None
    replay: bool = False


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def screened_text(key, body):
    """Normalize for storage and dedupe; this is not semantic moderation."""
    try:
        if type(key) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", key):
            raise ValueError("invalid suggestion key")
        if type(body) is not str or not 1 <= len(body) <= MAX_BODY:
            raise ValueError("invalid suggestion length")
        # Block hidden formatting and control characters before normalization.
        if any(unicodedata.category(c).startswith("C") for c in body):
            raise ValueError("invalid suggestion characters")
        normalized = " ".join(unicodedata.normalize("NFKC", body).split())
        if not 1 <= len(normalized) <= MAX_BODY or sum(c.isalnum() for c in normalized) < 3:
            raise ValueError("insufficient suggestion content")
        return normalized, digest(normalized), digest(normalized.casefold())
    except (ValueError, TypeError):
        logger.info("Suggestion shape rejected")
        raise
