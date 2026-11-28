"""Private community transport contract; no network or task execution."""
from dataclasses import dataclass, field
import logging
from uuid import UUID

from penny.bridge.state import wire_id
from .suggestion_state import screened_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CommunityClaim:
    id: UUID
    owner: UUID
    key: UUID
    fence: UUID
    expires_at: int
    lease_until: int
    text: str = field(repr=False)


def parse_community_claim(data, now):
    """Validate exact wire shape and current scoped ASCII admission contract."""
    try:
        if type(data) is not dict or set(data) != {
            "id", "owner", "key", "fence", "expiresAt", "leaseUntil", "text"
        }:
            raise ValueError("invalid community envelope")
        expiry, lease = data["expiresAt"], data["leaseUntil"]
        if not all(type(v) is int and 0 <= v < 2**53 for v in (now, expiry, lease)):
            raise ValueError("invalid community clock")
        if not now < lease <= expiry <= now + 3600 or lease > now + 900:
            raise ValueError("invalid community lease")
        key = wire_id(data["key"])
        text = data["text"]
        screened_text(str(key), text)
        if any(not 32 <= ord(c) <= 126 for c in text):
            raise ValueError("unsupported community encoding")
        return CommunityClaim(wire_id(data["id"]), wire_id(data["owner"]), key,
                              wire_id(data["fence"]), expiry, lease, text)
    except (ValueError, TypeError, OverflowError) as exc:
        logger.info("Community envelope rejected (%s)", type(exc).__name__)
        raise
