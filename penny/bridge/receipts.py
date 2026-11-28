"""Atomically admit mapped questions and retain replay-safe local receipts."""
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from uuid import UUID

from penny.guardian.policy import identity_matches
from .reply_db import reply_call
from .state import RemoteClaim, wire_text

logger = logging.getLogger(__name__)
MAX_RECEIPTS = 4096


@dataclass(frozen=True, slots=True)
class LocalReceipt:
    status: str
    task_id: UUID | None = None
    replayed: bool = False


def valid_id(value):
    return type(value) is UUID and value.int != 0


def admit_claim(dsn, claim):
    """Only trusted bridge invokes this; claims are still untrusted data."""
    try:
        if type(claim) is not RemoteClaim or not all(
            valid_id(x) for x in (claim.id,claim.owner,claim.fence)
        ):
            return LocalReceipt("invalid")
        wire_text(claim.text,2000)
        if type(claim.lease_until) is not datetime or claim.lease_until.tzinfo != timezone.utc:
            return LocalReceipt("invalid")
        expiry = int(claim.lease_until.timestamp())
    except (ValueError,TypeError,OverflowError,OSError):
        logger.warning("Bridge claim validation rejected")
        return LocalReceipt("invalid")
    # The database checks its own clock, local mapping and shared quotas.
    # Python identity verification is separate from the SQL role boundary.
    if not identity_matches():
        return LocalReceipt("identity_unavailable")
    row=reply_call(dsn,"admit",(claim.id,claim.owner,claim.fence,expiry,claim.text))
    if row is None or row["status"] not in (
        "accept","invalid","expired","denied","conflict","full","paused",
        "resting","member_limit","member_quota","community_quota"):
        raise RuntimeError("invalid bridge admission result")
    if (row["status"]=="accept")!=valid_id(row["task_id"]):
        raise RuntimeError("invalid bridge task receipt")
    if type(row["replayed"]) is not bool or (row["replayed"] and row["status"]!="accept"):
        raise RuntimeError("invalid bridge replay flag")
    return LocalReceipt(row["status"],row["task_id"],row["replayed"])


def record_ack(dsn,question_id,fence,task_id):
    """Record a confirmed remote acknowledgement, not new admission."""
    if not all(valid_id(x) for x in (question_id,fence,task_id)) or not identity_matches():
        return False
    row=reply_call(dsn,"ack",(question_id,fence,task_id))
    return row is not None and row["recorded"] is True
