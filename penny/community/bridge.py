"""Private operator-only community receipt candidate; no live bridge privileges."""
import logging
from uuid import UUID

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .intake import _submit_locked, _valid_replay
from .suggestion_state import SuggestionReceipt, screened_text, digest

logger = logging.getLogger(__name__)
MAX_RECEIPTS = 4096


def admit_community_claim(dsn, *, cloud_id, cloud_owner, key, fence, body,
                          expires_at, lease_until):
    """Map a trusted transport claim; never create identity from its payload."""
    try:
        if not all(type(v) is UUID and v.int for v in (cloud_id, cloud_owner, key, fence)):
            return SuggestionReceipt("denied")
        if not all(type(v) is int and 0 < v < 2**53 for v in (expires_at, lease_until)):
            return SuggestionReceipt("denied")
        decision = authorize(Actor.MEMBER, Capability.SUBMIT_SUGGESTION)
        if not decision.allowed:
            return SuggestionReceipt("denied")
        text, exact, duplicate = screened_text(str(key), body)
        raw_digest = digest(body)
        with locked(dsn) as (conn, control, now):
            if not now < lease_until <= expires_at <= now + 3600 or lease_until > now + 900:
                return SuggestionReceipt("denied")
            mapping = conn.execute(
                "SELECT local_member FROM bridge_member WHERE cloud_owner=%s AND enabled",
                (cloud_owner,)).fetchone()
            if not mapping:
                return SuggestionReceipt("denied")
            owner = mapping["local_member"]
            prior = conn.execute(
                "SELECT * FROM community_bridge_receipt WHERE cloud_id=%s",
                (cloud_id,)).fetchone()
            if prior:
                expected = (cloud_owner, owner, key, fence, raw_digest, expires_at, lease_until)
                actual = tuple(prior[k] for k in ("cloud_owner", "local_member",
                    "request_key", "fence", "payload_sha256", "expires_at", "lease_until"))
                if actual != expected:
                    return SuggestionReceipt("idempotency_conflict")
                row = conn.execute(
                    "SELECT * FROM community_suggestion WHERE id=%s AND member_id=%s",
                    (prior["suggestion_id"], owner)).fetchone()
                if not row or not _valid_replay(row, now) or row["duplicate_sha256"] != duplicate:
                    return SuggestionReceipt("denied")
                return SuggestionReceipt("accepted", prior["suggestion_id"], True)
            if control["paused"]:
                return SuggestionReceipt("paused")
            if conn.execute("SELECT 1 FROM community_bridge_receipt WHERE fence=%s OR (cloud_owner=%s AND request_key=%s)",
                            (fence, cloud_owner, key)).fetchone():
                return SuggestionReceipt("idempotency_conflict")
            if conn.execute("SELECT count(*) AS n FROM community_bridge_receipt").fetchone()["n"] >= MAX_RECEIPTS:
                return SuggestionReceipt("capacity")
            receipt = _submit_locked(conn, control, now, owner, str(key), text, exact, duplicate, decision)
            if receipt.status not in ("accepted", "duplicate"):
                return receipt
            # Same transaction: failure here rolls back new suggestion admission.
            conn.execute("INSERT INTO community_bridge_receipt VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                         (cloud_id, cloud_owner, owner, key, fence, raw_digest,
                          receipt.suggestion_id, expires_at, lease_until, now))
            return SuggestionReceipt("accepted", receipt.suggestion_id, receipt.replay)
    except Exception as exc:
        logger.error("Community bridge admission failed (%s)", type(exc).__name__)
        raise
