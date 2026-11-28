"""Shared community intake budget, called under the scheduler lock."""
import logging
from .suggestion_state import OWNER_DAILY,OWNER_PENDING,GLOBAL_DAILY,GLOBAL_PENDING,MAX_RECORDS

logger=logging.getLogger(__name__)


def capacity_reason(conn,owner,now):
    try:
        # Withdrawn ratings continue to count as attempts, not pending work.
        # Neither a new preview nor a different intake route resets limits.
        count=conn.execute(
            """WITH intake AS (
                SELECT s.member_id,s.submitted_at,r.suggestion_id IS NULL AS pending
                FROM community_suggestion s LEFT JOIN community_suggestion_review r
                ON r.suggestion_id=s.id
                UNION ALL
                SELECT f.member_id,f.submitted_at,
                    f.withdrawn_at IS NULL AND v.feedback_id IS NULL
                FROM workshop_feedback f LEFT JOIN workshop_feedback_review v
                ON v.feedback_id=f.id
            )
            SELECT count(*) AS total,
                count(*) FILTER (WHERE submitted_at>%s) AS daily,
                count(*) FILTER (WHERE member_id=%s AND submitted_at>%s) AS owner_daily,
                count(*) FILTER (WHERE pending) AS pending,
                count(*) FILTER (WHERE member_id=%s AND pending) AS owner_pending
            FROM intake""",(now-86400,owner,now-86400,owner)).fetchone()
        if count["owner_daily"]>=OWNER_DAILY or count["owner_pending"]>=OWNER_PENDING:
            return "member_limit"
        if count["total"]>=MAX_RECORDS or count["daily"]>=GLOBAL_DAILY or count["pending"]>=GLOBAL_PENDING:
            return "capacity"
        return None
    except Exception as exc:
        logger.error("Community intake capacity failed (%s)",type(exc).__name__)
        raise
