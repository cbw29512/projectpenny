"""Private suggestion status and bounded reviewer worklist; no task admission."""
import logging
from uuid import UUID

from penny.auth.session import resolve_member
from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .suggestion_state import digest

logger = logging.getLogger(__name__)
MAX_BATCH = 20


def own_status(dsn, token, suggestion_id):
    """Return only owner-scoped decision fields, never private idea text."""
    try:
        if type(suggestion_id) is not UUID or suggestion_id.int == 0:
            raise ValueError("invalid suggestion ID")
        if not authorize(Actor.MEMBER, Capability.READ_OWN_SUGGESTION).allowed:
            return None
        with locked(dsn) as (conn, _, now):
            owner = resolve_member(conn, now, token)
            row = conn.execute(
                """SELECT s.id,s.body,s.body_sha256,s.submitted_at,
                          r.body_sha256 AS reviewed_sha256,r.verdict,r.reason,r.reviewed_at
                   FROM community_suggestion s
                   LEFT JOIN community_suggestion_review r ON r.suggestion_id=s.id
                   WHERE s.id=%s AND s.member_id=%s""",
                (suggestion_id, owner),
            ).fetchone()
            if row is None:
                return None
            if (digest(row["body"]) != row["body_sha256"]
                    or row["submitted_at"] > now
                    or (row["verdict"] is not None and (
                        row["reviewed_sha256"] != row["body_sha256"]
                        or not row["submitted_at"] <= row["reviewed_at"] <= now))):
                return None
            return {"suggestion_id": str(row["id"]),
                    "status": row["verdict"] or "pending", "reason": row["reason"],
                    "submitted_at": row["submitted_at"], "reviewed_at": row["reviewed_at"]}
    except Exception as exc:
        logger.warning("Private suggestion status refused (%s)", type(exc).__name__)
        raise


def pending_suggestions(dsn, *, limit=MAX_BATCH):
    """Trusted reviewer only. Exclude identity, tokens and request keys."""
    try:
        if type(limit) is not int or not 1 <= limit <= MAX_BATCH:
            raise ValueError("invalid suggestion review batch")
        if not authorize(Actor.ADMIN, Capability.REVIEW_SUGGESTION).allowed:
            return ()
        with locked(dsn) as (conn, _, now):
            rows = conn.execute(
                """SELECT s.id,s.body,s.body_sha256,s.submitted_at
                   FROM community_suggestion s
                   LEFT JOIN community_suggestion_review r ON r.suggestion_id=s.id
                   WHERE r.suggestion_id IS NULL
                   ORDER BY s.submitted_at,s.id LIMIT %s""", (limit,),
            ).fetchall()
            items = []
            for row in rows:
                # Invalid rows are reported to the operator without disclosing
                # their potentially corrupted body or implying reviewability.
                valid = (digest(row["body"]) == row["body_sha256"]
                         and row["submitted_at"] <= now)
                items.append({"suggestion_id": str(row["id"]),
                              "body": row["body"] if valid else None,
                              "body_sha256": row["body_sha256"] if valid else None,
                              "submitted_at": row["submitted_at"],
                              "integrity_ok": valid})
            return tuple(items)
    except Exception as exc:
        logger.error("Suggestion review worklist unavailable (%s)", type(exc).__name__)
        raise
