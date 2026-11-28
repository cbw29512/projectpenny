"""Durable rolling admission budgets, checked under the scheduler lock."""
import logging
from .state import Tier

logger = logging.getLogger(__name__)
HOUR = 3600
DAY = 86400
# Provisional beta ceilings; no payment can bypass the aggregate limit.
FREE_LIMITS = (3, 10)
SUPPORTER_LIMITS = (10, 30)
GLOBAL_LIMITS = (20, 120)


def member_budget(conn, member, tier, now):
    """Return rejection code or None. Internal business work is separate.

    Count admissions, not just completed jobs, so errors and fresh sessions
    cannot reset budgets. Use the database clock and the existing global
    transaction lock to prevent concurrent check-then-insert races.
    """
    try:
        if member is None:
            return None
        limits = FREE_LIMITS if tier is Tier.FREE else SUPPORTER_LIMITS
        own = conn.execute(
            """SELECT count(*) FILTER (WHERE submitted_at>%s) AS hourly,
                      count(*) AS daily
               FROM work_task WHERE member_id=%s AND submitted_at>%s""",
            (now-HOUR,member,now-DAY),
        ).fetchone()
        if own["hourly"] >= limits[0] or own["daily"] >= limits[1]:
            return "member_quota"
        total = conn.execute(
            """SELECT count(*) FILTER (WHERE submitted_at>%s) AS hourly,
                      count(*) AS daily
               FROM work_task WHERE member_id IS NOT NULL AND submitted_at>%s""",
            (now-HOUR,now-DAY),
        ).fetchone()
        if total["hourly"] >= GLOBAL_LIMITS[0] or total["daily"] >= GLOBAL_LIMITS[1]:
            return "community_quota"
        return None
    except Exception as exc:
        # Abort admission rather than accepting work on an uncertain count.
        logger.error("Admission quota check failed (%s)",type(exc).__name__)
        raise
