"""Worker-only bounded personal recall; owner comes from fenced database task."""
import logging
from uuid import UUID

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .member_consent import active_consent
from .member_state import MemberPreference

logger = logging.getLogger(__name__)
MAX_PERSONAL_RECALL = 3


def recall_preferences(dsn,task_id,fence):
    try:
        if type(task_id) is not UUID or type(fence) is not UUID:
            return ()
        if not authorize(Actor.WORKER,Capability.RECALL_MEMBER_MEMORY).allowed:
            return ()
        with locked(dsn) as (conn,control,now):
            if control["paused"]:
                return ()
            scope = conn.execute(
                """SELECT s.member_id,s.epoch FROM member_recall_scope s
                   JOIN work_task t ON t.id=s.task_id AND t.member_id=s.member_id
                   WHERE t.id=%s AND t.fence=%s AND t.state='running' AND t.lease_until>%s""",
                (task_id,fence,now),
            ).fetchone()
            if not scope:
                return ()
            consent = active_consent(conn,scope["member_id"],now)
            if not consent or consent["epoch"] != scope["epoch"]:
                return ()
            # Do not change a previous inference snapshot under the same fence.
            if conn.execute("SELECT 1 FROM member_recall_snapshot WHERE task_id=%s",
                            (task_id,)).fetchone():
                raise RuntimeError("personal recall already performed")
            rows = conn.execute(
                """SELECT id,preference FROM member_memory WHERE member_id=%s AND epoch=%s
                   ORDER BY created_at DESC,id LIMIT %s""",
                (scope["member_id"],scope["epoch"],MAX_PERSONAL_RECALL),
            ).fetchall()
            if rows:
                conn.execute("INSERT INTO member_recall_snapshot VALUES (%s,%s,%s,%s)",
                             (task_id,fence,[r["id"] for r in rows],now))
            return tuple(MemberPreference(r["id"],r["preference"]) for r in rows)
    except Exception as exc:
        logger.error("Personal memory recall failed (%s)",type(exc).__name__)
        raise


def snapshot_valid(conn,row,now):
    """Called under the completion lock; reject stale consent/deleted preferences."""
    snapshot = conn.execute(
        """SELECT p.fence,p.preference_ids,s.member_id,s.epoch
           FROM member_recall_snapshot p JOIN member_recall_scope s ON s.task_id=p.task_id
           WHERE p.task_id=%s""",(row["id"],),
    ).fetchone()
    if not snapshot:
        return True
    if snapshot["fence"] != row["fence"] or snapshot["member_id"] != row["member_id"]:
        return False
    consent = active_consent(conn,snapshot["member_id"],now)
    if not consent or consent["epoch"] != snapshot["epoch"]:
        return False
    current = conn.execute(
        "SELECT id FROM member_memory WHERE member_id=%s AND epoch=%s AND id=ANY(%s::uuid[])",
        (snapshot["member_id"],snapshot["epoch"],snapshot["preference_ids"]),
    ).fetchall()
    return {r["id"] for r in current} == set(snapshot["preference_ids"])
