"""Private aggregate candidate only; never publishes or triggers inference."""
import logging
from uuid import UUID

from penny.business.preview import read_preview_locked
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.scheduler.storage_db import locked

logger=logging.getLogger(__name__)
# Provisional internal suppression floor, not anonymity or public consent.
MIN_SAMPLE=5


def feedback_summary(dsn,preview_id):
    try:
        if type(preview_id) is not UUID or preview_id.int==0:
            raise ValueError("invalid preview ID")
        if not authorize(Actor.ADMIN,Capability.REVIEW_SUGGESTION).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            return summary_locked(conn,preview_id,now)
    except Exception as exc:
        logger.error("Workshop feedback aggregation failed (%s)",type(exc).__name__)
        raise


def summary_locked(conn,preview_id,now):
    """Trusted caller holds scheduler lock; no separate transaction or publication."""
    preview=read_preview_locked(conn,preview_id,now)
    if preview is None:
        return None
    row=conn.execute(
        """SELECT count(*) AS n,sum(f.usefulness) AS rating_sum,
           count(*) FILTER(WHERE f.purchase_interest='yes') AS yes_count,
           count(*) FILTER(WHERE f.purchase_interest='maybe') AS maybe_count,
           count(*) FILTER(WHERE f.purchase_interest='no') AS no_count
           FROM workshop_feedback f JOIN workshop_feedback_review r ON r.feedback_id=f.id
           WHERE f.preview_id=%s AND f.preview_sha256=%s
           AND r.preview_sha256=f.preview_sha256 AND r.verdict='eligible'
           AND f.withdrawn_at IS NULL""",
        (preview_id,preview["preview_sha256"])).fetchone()
    base={"preview_id":str(preview_id),"preview_sha256":preview["preview_sha256"],
          "observed_at":now,"self_reported":True,"commercial_authority":False}
    if row["n"]<MIN_SAMPLE:
        return base|{"status":"insufficient_sample"}
    # Exact integer total and count avoid floating rounding ambiguity.
    # Internal only: a public view would require separate privacy review.
    return base|{"status":"available","eligible_count":row["n"],
                 "usefulness_sum":row["rating_sum"],
                 "interest":{"yes":row["yes_count"],"maybe":row["maybe_count"],
                             "no":row["no_count"]}}
