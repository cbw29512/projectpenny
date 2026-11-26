"""Trusted local reviewer only. No public route or scheduling side effects."""
import logging
import re
from uuid import UUID

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .suggestion_state import Verdict, REASONS, digest

logger = logging.getLogger(__name__)


def review_suggestion(dsn, suggestion_id, *, expected_sha256, verdict, reason, reviewer_id):
    try:
        decision = authorize(Actor.ADMIN, Capability.REVIEW_SUGGESTION)
        if not decision.allowed:
            return False
        if (type(suggestion_id) is not UUID or not suggestion_id.int
                or type(reviewer_id) is not UUID or not reviewer_id.int
                or type(expected_sha256) is not str or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256)
                or type(verdict) is not Verdict or type(reason) is not str or reason not in REASONS[verdict]):
            raise ValueError("invalid suggestion review")
        with locked(dsn) as (conn, _, now):
            row = conn.execute(
                "SELECT body,body_sha256 FROM community_suggestion WHERE id=%s",
                (suggestion_id,),
            ).fetchone()
            if not row or row["body_sha256"] != expected_sha256 or digest(row["body"]) != expected_sha256:
                return False
            previous = conn.execute(
                "SELECT verdict,reason,reviewer_id,body_sha256 FROM community_suggestion_review WHERE suggestion_id=%s",
                (suggestion_id,),
            ).fetchone()
            if previous:
                return (previous["verdict"], previous["reason"], previous["reviewer_id"], previous["body_sha256"]) == (
                    verdict.value, reason, reviewer_id, expected_sha256)
            conn.execute(
                "INSERT INTO community_suggestion_review VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (suggestion_id, expected_sha256, verdict.value, reason, reviewer_id, now, decision.policy_version),
            )
            return True
    except Exception as exc:
        logger.error("Suggestion review failed (%s)", type(exc).__name__)
        raise
