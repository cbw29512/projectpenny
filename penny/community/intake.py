"""Authenticated, transactional, private intake. No inference on admission."""
import logging
from uuid import uuid4

from penny.auth.session import resolve_member
from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .suggestion_state import (
    SuggestionReceipt, screened_text, digest,
)

from .quota import capacity_reason

logger = logging.getLogger(__name__)


def _valid_replay(row, now):
    # A receipt must refer to intact content and a plausible database timestamp.
    return (0 <= row["submitted_at"] <= now
            and digest(row["body"]) == row["body_sha256"]
            and digest(row["body"].casefold()) == row["duplicate_sha256"])


def submit_suggestion(dsn, token, *, key, body):
    try:
        decision = authorize(Actor.MEMBER, Capability.SUBMIT_SUGGESTION)
        if not decision.allowed:
            return SuggestionReceipt("denied")
        text, exact, duplicate = screened_text(key, body)
        with locked(dsn) as (conn, control, now):
            owner = resolve_member(conn, now, token)
            return _submit_locked(conn, control, now, owner, key, text, exact, duplicate, decision)
    except Exception as exc:
        logger.error("Suggestion intake failed (%s)", type(exc).__name__)
        raise


def _submit_locked(conn, control, now, owner, key, text, exact, duplicate, decision):
    """Private shared admission under the existing scheduler lock."""
    prior = conn.execute(
        "SELECT id,body,body_sha256,duplicate_sha256,submitted_at FROM community_suggestion WHERE member_id=%s AND request_key=%s",
        (owner, key),
    ).fetchone()
    if prior:
        if not _valid_replay(prior, now):
            return SuggestionReceipt("denied")
        if prior["body_sha256"] != exact:
            return SuggestionReceipt("idempotency_conflict")
        return SuggestionReceipt("accepted", prior["id"], True)
    old = conn.execute(
        "SELECT id,body,body_sha256,duplicate_sha256,submitted_at FROM community_suggestion WHERE member_id=%s AND duplicate_sha256=%s",
        (owner, duplicate),
    ).fetchone()
    if old:
        if not _valid_replay(old, now):
            return SuggestionReceipt("denied")
        # Do not bind an unused key to a different original request.
        return SuggestionReceipt("duplicate", old["id"], True)
    if control["paused"]:
        return SuggestionReceipt("paused")
    reason=capacity_reason(conn,owner,now)
    if reason:
        return SuggestionReceipt(reason)
    suggestion_id = uuid4()
    conn.execute(
        """INSERT INTO community_suggestion
        (id,member_id,request_key,body,body_sha256,duplicate_sha256,submitted_at,policy_version)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (suggestion_id, owner, key, text, exact, duplicate, now, decision.policy_version),
    )
    return SuggestionReceipt("accepted", suggestion_id)
