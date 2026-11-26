"""Trusted operator stages or rejects quotes; zero spending authority."""
import logging
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id, _valid_ref
from penny.scheduler.storage_db import locked
from .state import MAX_CENTS, JournalReceipt
from .spend_state import Purpose, Rejection, MAX_QUOTE_AGE

logger=logging.getLogger(__name__)


def stage(dsn, *, source_ref, purpose, cents, quote_ref, evidence, reviewer_id, expires_at):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_SPEND_REQUEST)
        if not decision.allowed:
            return None
        if (not _valid_ref(source_ref) or not _valid_ref(quote_ref)
                or not _valid_id(reviewer_id) or type(purpose) is not Purpose
                or type(cents) is not int or not 1<=cents<=MAX_CENTS
                or type(expires_at) is not int):
            raise ValueError("invalid spend request")
        request_id=uuid4()
        mark=fingerprint(request_id,evidence)
        with locked(dsn) as (conn,_,now):
            old=conn.execute("SELECT * FROM vault_spend_request WHERE source_ref=%s",
                             (source_ref,)).fetchone()
            expected=(purpose.value,cents,quote_ref,mark.digest,mark.byte_count,reviewer_id,expires_at)
            if old:
                fields=("purpose","cents","quote_ref","evidence_sha256","evidence_size","reviewer_id","expires_at")
                if tuple(old[k] for k in fields)!=expected:
                    raise ValueError("conflicting request")
                return JournalReceipt(old["id"],True)
            if not now<expires_at<=now+MAX_QUOTE_AGE:
                raise ValueError("invalid quote expiry")
            conn.execute("""INSERT INTO vault_spend_request
                (id,source_ref,purpose,cents,quote_ref,evidence_sha256,evidence_size,
                 reviewer_id,created_at,expires_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (request_id,source_ref,purpose.value,cents,quote_ref,mark.digest,
                 mark.byte_count,reviewer_id,now,expires_at,decision.policy_version))
            return JournalReceipt(request_id)
    except Exception as exc:
        logger.error("Spend request refused (%s)",type(exc).__name__)
        raise


def reject(dsn, request_id, *, reviewer_id, reason):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_SPEND_REQUEST)
        if not decision.allowed:
            return False
        if not _valid_id(request_id) or not _valid_id(reviewer_id) or type(reason) is not Rejection:
            raise ValueError("invalid rejection")
        with locked(dsn) as (conn,_,now):
            row=conn.execute("SELECT expires_at FROM vault_spend_request WHERE id=%s",
                             (request_id,)).fetchone()
            if not row or row["expires_at"]<=now:
                return False
            if conn.execute("SELECT 1 FROM vault_reservation WHERE request_id=%s",(request_id,)).fetchone():
                return False
            return conn.execute("""INSERT INTO vault_spend_rejection VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(request_id) DO NOTHING RETURNING request_id""",
                (request_id,reviewer_id,reason.value,now,decision.policy_version)).fetchone() is not None
    except Exception as exc:
        logger.error("Spend rejection refused (%s)",type(exc).__name__)
        raise


def status(dsn, request_id):
    try:
        if not _valid_id(request_id):
            raise ValueError("invalid request")
        with locked(dsn) as (conn,_,now):
            row=conn.execute("""SELECT q.cents,q.expires_at,r.reason,h.request_id AS hold,x.request_id AS released
                FROM vault_spend_request q LEFT JOIN vault_spend_rejection r ON r.request_id=q.id
                LEFT JOIN vault_reservation h ON h.request_id=q.id
                LEFT JOIN vault_reservation_release x ON x.request_id=q.id
                WHERE q.id=%s""",(request_id,)).fetchone()
            if not row:
                return None
            state="rejected" if row["reason"] else "expired" if row["expires_at"]<=now else "pending"
            if row["hold"]:
                state="released" if row["released"] else "reserved_expired" if row["expires_at"]<=now else "reserved"
            return {"status":state,"requested_cents":row["cents"],"reason":row["reason"],
                    "authorized_cents":0,"reserved_cents":row["cents"] if row["hold"] and not row["released"] else 0}
    except Exception as exc:
        logger.error("Spend status unavailable (%s)",type(exc).__name__)
        raise
