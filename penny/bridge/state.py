"""Bounded wire types shared by the private bridge transport."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from penny.community.transport_state import CommunityClaim


@dataclass(frozen=True, slots=True)
class RemoteClaim:
    id: UUID
    owner: UUID
    fence: UUID
    lease_until: datetime
    text: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class BridgeResult:
    status: str
    claim: "RemoteClaim | CommunityClaim | None" = None
    retry_after: int = 0


def wire_id(value):
    if type(value) is not str:
        raise ValueError("invalid identifier")
    parsed = UUID(value)
    if parsed.int == 0 or str(parsed) != value:
        raise ValueError("invalid identifier")
    return parsed


def wire_text(value, limit):
    if (type(value) is not str or not value.strip() or len(value) > limit
            or "\x00" in value or len(value.encode("utf-8")) > limit * 4):
        raise ValueError("invalid text")
    return value


def parse_claim(data, now):
    # Cloud fields are untrusted, including identity and expiration.
    if type(data) is not dict or set(data) != {
        "status", "id", "owner", "fence", "leaseUntil", "text"
    } or data["status"] != "claimed":
        raise ValueError("invalid claim")
    raw = data["leaseUntil"]
    if type(raw) is not str or len(raw) != 24 or not raw.endswith("Z"):
        raise ValueError("invalid lease")
    expiry = datetime.fromisoformat(raw[:-1] + "+00:00")
    if (expiry.tzinfo != timezone.utc or expiry <= now
            or (expiry - now).total_seconds() > 900):
        raise ValueError("expired or excessive lease")
    return RemoteClaim(wire_id(data["id"]), wire_id(data["owner"]),
                       wire_id(data["fence"]), expiry, wire_text(data["text"], 2000))
