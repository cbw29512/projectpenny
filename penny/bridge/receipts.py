"""Atomically admit mapped questions and retain replay-safe local receipts."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import logging
from uuid import UUID

from penny.guardian.policy import identity_matches
from penny.scheduler.admit import BRIDGE_PREFIX, submit_locked
from penny.scheduler.storage_db import locked
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
        digest = hashlib.sha256(claim.text.encode("utf-8")).hexdigest()
    except (ValueError,TypeError,OverflowError,OSError):
        logger.warning("Bridge claim validation rejected")
        return LocalReceipt("invalid")
    with locked(dsn) as (conn,control,now):
        if not identity_matches():
            return LocalReceipt("identity_unavailable")
        if not now + 5 < expiry <= now + 900:
            return LocalReceipt("expired")
        mapping = conn.execute(
            "SELECT local_member FROM bridge_member WHERE cloud_owner=%s AND enabled FOR UPDATE",
            (claim.owner,),
        ).fetchone()
        if mapping is None:
            return LocalReceipt("denied")
        member = mapping["local_member"]
        old = conn.execute(
            "SELECT * FROM bridge_receipt WHERE question_id=%s",(claim.id,)
        ).fetchone()
        if old:
            if (old["cloud_owner"],old["local_member"],old["fence"],
                    old["payload_sha256"],old["expires_at"]) != (
                    claim.owner,member,claim.fence,digest,expiry):
                return LocalReceipt("conflict")
            return LocalReceipt("accept",old["task_id"],True)
        if conn.execute("SELECT 1 FROM bridge_receipt WHERE fence=%s",(claim.fence,)).fetchone():
            return LocalReceipt("conflict")
        if conn.execute("SELECT count(*) AS n FROM bridge_receipt").fetchone()["n"] >= MAX_RECEIPTS:
            return LocalReceipt("full")
        # Never request personal memories or bypass the existing local quotas.
        # Same transaction: a crash cannot leave an admitted orphan task.
        receipt = submit_locked(conn,control,now,member,BRIDGE_PREFIX+str(claim.id),
                                claim.text,deadline_cap=expiry-5)
        if receipt.status != "accept":
            return LocalReceipt(receipt.status)
        if receipt.replayed:
            # A missing receipt must not be silently repaired from a bare task.
            raise RuntimeError("bridge receipt integrity failure")
        conn.execute(
            """INSERT INTO bridge_receipt
            (question_id,cloud_owner,local_member,fence,task_id,payload_sha256,expires_at,admitted_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (claim.id,claim.owner,member,claim.fence,receipt.task_id,digest,expiry,now),
        )
        return LocalReceipt("accept",receipt.task_id)


def record_ack(dsn, question_id, fence, task_id):
    """Record only an already-confirmed remote acknowledgement (trusted caller)."""
    if not all(valid_id(x) for x in (question_id,fence,task_id)):
        return False
    with locked(dsn) as (conn,_,now):
        if not identity_matches():
            return False
        row = conn.execute(
            """SELECT r.acked_at FROM bridge_receipt r JOIN bridge_member m
            ON m.cloud_owner=r.cloud_owner AND m.local_member=r.local_member AND m.enabled
            WHERE r.question_id=%s AND r.fence=%s AND r.task_id=%s AND r.expires_at>%s
            FOR UPDATE OF r,m""",(question_id,fence,task_id,now)
        ).fetchone()
        if row is None:
            return False
        if row["acked_at"] is None:
            conn.execute("UPDATE bridge_receipt SET acked_at=%s WHERE question_id=%s",
                         (now,question_id))
        return True
