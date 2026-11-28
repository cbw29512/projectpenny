"""Narrow local adapter for a validated community transport claim."""
import logging
import time

from penny.bridge.reply_db import reply_call
from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from .transport_state import CommunityClaim, parse_community_claim

logger = logging.getLogger(__name__)


def persist_claim(dsn, claim):
    """Return true only after the scoped DB call commits; no remote ack here."""
    try:
        if type(claim) is not CommunityClaim:
            return False
        if not authorize(Actor.MEMBER, Capability.SUBMIT_SUGGESTION).allowed:
            return False
        data = dict(id=str(claim.id), owner=str(claim.owner), key=str(claim.key),
                    fence=str(claim.fence), expiresAt=claim.expires_at,
                    leaseUntil=claim.lease_until, text=claim.text)
        if parse_community_claim(data, int(time.time())) != claim:
            return False
        row = reply_call(dsn, "community_admit", (
            claim.id, claim.owner, claim.key, claim.fence, claim.text,
            claim.expires_at, claim.lease_until))
        return row is not None and row["recorded"] is True
    except Exception as exc:
        logger.warning("Community persistence refused (%s)", type(exc).__name__)
        return False
