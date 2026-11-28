"""Private token-only feedback intake; never expose the underlying artifact."""
import logging
from uuid import UUID,uuid4

from penny.auth.session import resolve_member
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.scheduler.storage_db import locked
from penny.business.preview import read_preview_locked
from .feedback_state import FeedbackReceipt,validate_feedback
from .quota import capacity_reason

logger=logging.getLogger(__name__)


def submit_feedback(dsn,token,*,preview_id,preview_sha256,key,usefulness,purchase_interest):
    try:
        decision=authorize(Actor.MEMBER,Capability.SUBMIT_SUGGESTION)
        if not decision.allowed:
            return FeedbackReceipt("denied")
        validate_feedback(preview_id,preview_sha256,key,usefulness,purchase_interest)
        with locked(dsn) as (conn,control,now):
            owner=resolve_member(conn,now,token)
            prior=conn.execute(
                """SELECT id,preview_id,preview_sha256,usefulness,purchase_interest,withdrawn_at
                FROM workshop_feedback WHERE member_id=%s AND request_key=%s""",(owner,key)).fetchone()
            if prior:
                # Withdrawal removes rating values, not the immutable preview identity.
                # A reused key must never acknowledge a different preview/version.
                if (prior["preview_id"],prior["preview_sha256"])!=(preview_id,preview_sha256):
                    return FeedbackReceipt("idempotency_conflict")
                if prior["withdrawn_at"] is not None:
                    return FeedbackReceipt("withdrawn",prior["id"],True)
                if tuple(prior[k] for k in ("preview_id","preview_sha256","usefulness","purchase_interest"))!=(
                        preview_id,preview_sha256,usefulness,purchase_interest):
                    return FeedbackReceipt("idempotency_conflict")
                return FeedbackReceipt("accepted",prior["id"],True)
            if control["paused"]:
                return FeedbackReceipt("paused")
            # Exact reviewed version, still live; no user-selected raw artifact.
            preview=read_preview_locked(conn,preview_id,now)
            if preview is None or preview["preview_sha256"]!=preview_sha256:
                return FeedbackReceipt("unavailable")
            old=conn.execute(
                "SELECT id,withdrawn_at FROM workshop_feedback WHERE member_id=%s AND preview_id=%s",
                (owner,preview_id)).fetchone()
            if old:
                return FeedbackReceipt("withdrawn" if old["withdrawn_at"] is not None else "already_rated",old["id"])
            reason=capacity_reason(conn,owner,now)
            if reason:
                return FeedbackReceipt(reason)
            fid=uuid4()
            conn.execute(
                """INSERT INTO workshop_feedback(id,preview_id,preview_sha256,member_id,
                    request_key,usefulness,purchase_interest,submitted_at,policy_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (fid,preview_id,preview_sha256,owner,key,usefulness,purchase_interest,now,decision.policy_version))
            return FeedbackReceipt("accepted",fid)
    except Exception as exc:
        logger.error("Workshop feedback intake failed (%s)",type(exc).__name__)
        raise


def own_feedback(dsn,token,feedback_id):
    try:
        if type(feedback_id) is not UUID or feedback_id.int==0:
            raise ValueError("invalid feedback ID")
        with locked(dsn) as (conn,_,now):
            owner=resolve_member(conn,now,token)
            return conn.execute(
                """SELECT f.id,f.preview_id,f.preview_sha256,f.usefulness,f.purchase_interest,
                    f.submitted_at,f.withdrawn_at,
                    CASE WHEN f.withdrawn_at IS NOT NULL THEN 'withdrawn'
                         ELSE coalesce(r.verdict,'pending') END AS moderation
                    FROM workshop_feedback f LEFT JOIN workshop_feedback_review r ON r.feedback_id=f.id
                    WHERE f.id=%s AND f.member_id=%s""",(feedback_id,owner)).fetchone()
    except Exception as exc:
        logger.error("Workshop feedback read failed (%s)",type(exc).__name__)
        raise


def withdraw_feedback(dsn,token,feedback_id):
    """Owner privacy action remains available during pause or identity drift."""
    try:
        if type(feedback_id) is not UUID or feedback_id.int==0:
            raise ValueError("invalid feedback ID")
        with locked(dsn) as (conn,_,now):
            owner=resolve_member(conn,now,token)
            row=conn.execute(
                """UPDATE workshop_feedback SET usefulness=NULL,purchase_interest=NULL,
                    withdrawn_at=greatest(submitted_at,%s)
                    WHERE id=%s AND member_id=%s AND withdrawn_at IS NULL RETURNING id""",
                (now,feedback_id,owner)).fetchone()
            return row is not None
    except Exception as exc:
        logger.error("Workshop feedback withdrawal failed (%s)",type(exc).__name__)
        raise
