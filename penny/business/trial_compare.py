"""Private comparison of independently admitted competency trial artifacts."""
import logging
from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.review import _valid_id
from penny.scheduler.storage_db import locked
from .revision_compare import _compare, _quality
from .workshop_intake import read_locked

logger = logging.getLogger(__name__)


def compare_trials(dsn, before_id, after_id):
    """Compare exact stored artifacts; never imply verified revision lineage."""
    try:
        if not all(_valid_id(x) for x in (before_id, after_id)) or before_id == after_id:
            raise ValueError("distinct valid trial IDs required")
        if not authorize(Actor.ADMIN, Capability.REVIEW_BUSINESS_EXPERIMENT).allowed:
            return None
        with locked(dsn) as (conn, _, now):
            before = read_locked(conn, before_id, now)
            after = read_locked(conn, after_id, now)
            result = {
                "before_task_id": str(before_id), "after_task_id": str(after_id),
                "revision_lineage_verified": False, "improvement_verified": False,
                "commercial_release_authorized": False, "comparison": None,
            }
            if any(not x or x["status"] != "private_prototype" for x in (before, after)):
                return result | {"status": "artifacts_unavailable"}
            old, new = before["artifact"], after["artifact"]
            return result | {
                "status": "available",
                "before": old | {"quality_status": _quality(conn, before_id, old["content_sha256"])},
                "after": new | {"quality_status": _quality(conn, after_id, new["content_sha256"])},
                "comparison": _compare(old["content"], new["content"]),
            }
    except Exception as exc:
        logger.error("Private trial comparison failed (%s)", type(exc).__name__)
        raise
