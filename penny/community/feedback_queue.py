"""Bounded private moderation worklist. Not a public or model-facing API."""
import logging

from penny.business.preview import read_preview_locked
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.scheduler.storage_db import locked

logger=logging.getLogger(__name__)
MAX_BATCH=20


def pending_feedback(dsn,*,limit=MAX_BATCH):
    """Trusted local reviewer only; include stale rows for rejection.

    Never return member identity, request keys, private product text, or
    evidence. Exact values are supplied for the existing fenced review.
    """
    try:
        if type(limit) is not int or not 1<=limit<=MAX_BATCH:
            raise ValueError("invalid moderation batch")
        if not authorize(Actor.ADMIN,Capability.REVIEW_SUGGESTION).allowed:
            return ()
        with locked(dsn) as (conn,_,now):
            rows=conn.execute(
                """SELECT f.id,f.preview_id,f.preview_sha256,f.usefulness,
                   f.purchase_interest,f.submitted_at
                   FROM workshop_feedback f
                   LEFT JOIN workshop_feedback_review r ON r.feedback_id=f.id
                   WHERE r.feedback_id IS NULL AND f.withdrawn_at IS NULL
                   ORDER BY f.submitted_at,f.id LIMIT %s""",(limit,)).fetchall()
            # Cache integrity checks within this transaction, not across reads.
            previews={}
            items=[]
            for row in rows:
                preview_id=row["preview_id"]
                if preview_id not in previews:
                    previews[preview_id]=read_preview_locked(conn,preview_id,now)
                preview=previews[preview_id]
                available=bool(preview and preview["preview_sha256"]==row["preview_sha256"])
                items.append({"feedback_id":row["id"],"preview_id":preview_id,
                    "preview_sha256":row["preview_sha256"],"usefulness":row["usefulness"],
                    "purchase_interest":row["purchase_interest"],
                    "submitted_at":row["submitted_at"],"preview_available":available})
            return tuple(items)
    except Exception as exc:
        logger.error("Feedback worklist unavailable (%s)",type(exc).__name__)
        raise
