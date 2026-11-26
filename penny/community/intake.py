"""Authenticated, transactional, private intake. No inference on admission."""
import logging
from uuid import uuid4

from penny.auth.session import resolve_member
from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .suggestion_state import (
    SuggestionReceipt, screened_text, OWNER_DAILY, OWNER_PENDING,
    GLOBAL_DAILY, GLOBAL_PENDING, MAX_RECORDS,
)

logger = logging.getLogger(__name__)


def submit_suggestion(dsn, token, *, key, body):
    try:
        decision = authorize(Actor.MEMBER, Capability.SUBMIT_SUGGESTION)
        if not decision.allowed:
            return SuggestionReceipt("denied")
        text, exact, duplicate = screened_text(key, body)
        with locked(dsn) as (conn, control, now):
            owner = resolve_member(conn, now, token)
            prior = conn.execute(
                "SELECT id,body_sha256 FROM community_suggestion WHERE member_id=%s AND request_key=%s",
                (owner, key),
            ).fetchone()
            if prior:
                if prior["body_sha256"] != exact:
                    return SuggestionReceipt("idempotency_conflict")
                return SuggestionReceipt("accepted", prior["id"], True)
            old = conn.execute(
                "SELECT id FROM community_suggestion WHERE member_id=%s AND duplicate_sha256=%s",
                (owner, duplicate),
            ).fetchone()
            if old:
                # Do not bind an unused key to a different original request.
                return SuggestionReceipt("duplicate", old["id"], True)
            if control["paused"]:
                return SuggestionReceipt("paused")
            count = conn.execute(
                """SELECT count(*) AS total,
                count(*) FILTER (WHERE s.submitted_at>%s) AS daily,
                count(*) FILTER (WHERE s.member_id=%s AND s.submitted_at>%s) AS owner_daily,
                count(*) FILTER (WHERE r.suggestion_id IS NULL) AS pending,
                count(*) FILTER (WHERE s.member_id=%s AND r.suggestion_id IS NULL) AS owner_pending
                FROM community_suggestion s LEFT JOIN community_suggestion_review r
                ON r.suggestion_id=s.id""",
                (now - 86400, owner, now - 86400, owner),
            ).fetchone()
            if count["owner_daily"] >= OWNER_DAILY or count["owner_pending"] >= OWNER_PENDING:
                return SuggestionReceipt("member_limit")
            if count["total"] >= MAX_RECORDS or count["daily"] >= GLOBAL_DAILY or count["pending"] >= GLOBAL_PENDING:
                return SuggestionReceipt("capacity")
            suggestion_id = uuid4()
            conn.execute(
                """INSERT INTO community_suggestion
                (id,member_id,request_key,body,body_sha256,duplicate_sha256,submitted_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (suggestion_id, owner, key, text, exact, duplicate, now, decision.policy_version),
            )
            return SuggestionReceipt("accepted", suggestion_id)
    except Exception as exc:
        logger.error("Suggestion intake failed (%s)", type(exc).__name__)
        raise
