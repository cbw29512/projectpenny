"""Atomic nonbinding holds; no payment authority or execution tokens."""
import logging

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id, _valid_ref
from penny.scheduler.storage_db import locked
from .budget import _budget

logger=logging.getLogger(__name__)


def reserve(dsn, request_id, *, budget_id, expected_cents, expected_quote_sha256,
            reviewer_id, confirmed):
    try:
        decision=authorize(Actor.ADMIN,Capability.RESERVE_VAULT_FUNDS)
        if not decision.allowed:
            return False
        if (confirmed is not True or not all(_valid_id(x) for x in
                (request_id,budget_id,reviewer_id)) or type(expected_cents) is not int
                or expected_cents<=0 or type(expected_quote_sha256) is not str):
            raise ValueError("invalid reservation review")
        with locked(dsn) as (conn,_,now):
            q=conn.execute("SELECT * FROM vault_spend_request WHERE id=%s",(request_id,)).fetchone()
            if (not q or q["expires_at"]<=now or q["cents"]!=expected_cents
                    or q["evidence_sha256"]!=expected_quote_sha256):
                return False
            if conn.execute("SELECT 1 FROM vault_spend_rejection WHERE request_id=%s",(request_id,)).fetchone():
                return False
            if conn.execute("SELECT 1 FROM vault_reservation WHERE request_id=%s",(request_id,)).fetchone():
                return False
            row,_,capacity,valid=_budget(conn,now)
            if not valid or row["id"]!=budget_id or q["cents"]>capacity:
                return False
            conn.execute("INSERT INTO vault_reservation VALUES (%s,%s,%s,%s,%s)",
                         (request_id,budget_id,reviewer_id,now,decision.policy_version))
            return True
    except Exception as exc:
        logger.error("Vault reservation refused (%s)",type(exc).__name__)
        raise


def release(dsn,request_id,*,reviewer_id,evidence_ref,evidence,no_commitment_confirmed):
    """Only release after confirming no payment or external obligation exists."""
    try:
        decision=authorize(Actor.ADMIN,Capability.RESERVE_VAULT_FUNDS)
        if not decision.allowed:
            return False
        if (no_commitment_confirmed is not True or not _valid_id(request_id)
                or not _valid_id(reviewer_id) or not _valid_ref(evidence_ref)):
            raise ValueError("invalid release")
        mark=fingerprint(request_id,evidence)
        with locked(dsn) as (conn,_,now):
            if not conn.execute("SELECT 1 FROM vault_reservation WHERE request_id=%s",(request_id,)).fetchone():
                return False
            return conn.execute("""INSERT INTO vault_reservation_release
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(request_id) DO NOTHING RETURNING request_id""",
                (request_id,reviewer_id,now,evidence_ref,mark.digest,mark.byte_count,
                 decision.policy_version)).fetchone() is not None
    except Exception as exc:
        logger.error("Vault reservation release refused (%s)",type(exc).__name__)
        raise
