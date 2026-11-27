"""Trusted local moderation; feedback is advice, not work authorization."""
import logging
import re
from uuid import UUID

from penny.business.preview import read_preview_locked
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.scheduler.storage_db import locked

logger=logging.getLogger(__name__)
REASONS={"eligible":frozenset({"valid_feedback"}),
         "rejected":frozenset({"spam","abuse","integrity"})}


def review_feedback(dsn,feedback_id,*,expected_preview_sha256,
                    expected_usefulness,expected_interest,verdict,reason,reviewer_id):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_SUGGESTION)
        if not decision.allowed:
            return False
        # Bind the human review to exact displayed values; no rating is
        # copied into the immutable review table or retained on withdrawal.
        if (any(type(v) is not UUID or not v.int for v in (feedback_id,reviewer_id))
                or type(expected_preview_sha256) is not str
                or not re.fullmatch(r"[a-f0-9]{64}",expected_preview_sha256)
                or type(expected_usefulness) is not int or not 1<=expected_usefulness<=5
                or type(expected_interest) is not str or expected_interest not in ("yes","maybe","no")
                or type(verdict) is not str or verdict not in REASONS
                or type(reason) is not str or reason not in REASONS[verdict]):
            raise ValueError("invalid feedback review")
        with locked(dsn) as (conn,_,now):
            row=conn.execute(
                """SELECT preview_id,preview_sha256,usefulness,purchase_interest,withdrawn_at
                   FROM workshop_feedback WHERE id=%s""",(feedback_id,)).fetchone()
            if (not row or row["withdrawn_at"] is not None
                    or (row["preview_sha256"],row["usefulness"],row["purchase_interest"])!=(
                        expected_preview_sha256,expected_usefulness,expected_interest)):
                return False
            prior=conn.execute(
                """SELECT preview_sha256,verdict,reason,reviewer_id
                   FROM workshop_feedback_review WHERE feedback_id=%s""",(feedback_id,)).fetchone()
            if prior:
                return tuple(prior[k] for k in ("preview_sha256","verdict","reason","reviewer_id"))==(
                    expected_preview_sha256,verdict,reason,reviewer_id)
            # Eligibility requires a still-valid reviewed preview. Rejection
            # remains possible after expiry or withdrawal to clear pending work.
            if verdict=="eligible":
                preview=read_preview_locked(conn,row["preview_id"],now)
                if preview is None or preview["preview_sha256"]!=expected_preview_sha256:
                    return False
            conn.execute(
                """INSERT INTO workshop_feedback_review
                   (feedback_id,preview_sha256,verdict,reason,reviewer_id,reviewed_at,policy_version)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (feedback_id,expected_preview_sha256,verdict,reason,reviewer_id,now,
                 decision.policy_version))
            return True
    except Exception as exc:
        logger.error("Workshop feedback moderation failed (%s)",type(exc).__name__)
        raise
