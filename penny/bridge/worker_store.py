"""Persistent bridge scheduling, separate from the inference transaction."""
import logging
from contextlib import contextmanager

import psycopg

from penny.guardian.policy import identity_matches
from penny.scheduler.storage_db import locked, expire_waiting
from .worker_state import Action

logger = logging.getLogger(__name__)
INTERVAL = 60
# Database-wide advisory lock: independent of the scheduler row lock.
LOCK_ID = 724390581215031

@contextmanager
def exclusive_cycle(dsn):
    try:
        with psycopg.connect(dsn,autocommit=True,connect_timeout=5) as conn:
            conn.execute("SET statement_timeout='5s'")
            acquired=conn.execute("SELECT pg_try_advisory_lock(%s)",(LOCK_ID,)).fetchone()[0]
            try:
                yield acquired
            finally:
                if acquired:
                    conn.execute("SELECT pg_advisory_unlock(%s)",(LOCK_ID,))
    except Exception as exc:
        logger.error("Bridge cycle lock failed (%s)",type(exc).__name__)
        raise


def reserve_action(dsn):
    # Reserve before any external effect; restart cannot erase cooldown.
    with locked(dsn) as (conn,control,now):
        gate=conn.execute("SELECT * FROM bridge_control WHERE singleton FOR UPDATE").fetchone()
        if (gate is None or not gate["enabled"] or gate["blocked_reason"] is not None
                or control["paused"] or not identity_matches()):
            return Action("paused"),INTERVAL
        if gate["not_before"]>now:
            return Action("cooldown"),gate["not_before"]-now
        conn.execute("UPDATE bridge_control SET not_before=%s WHERE singleton",(now+INTERVAL,))
        expire_waiting(conn,now)
        row=conn.execute(
            """SELECT r.question_id,r.fence,r.task_id,r.acked_at,
                      t.state,m.enabled,m.local_member=r.local_member AS mapped
               FROM bridge_receipt r JOIN work_task t ON t.id=r.task_id
               JOIN bridge_member m ON m.cloud_owner=r.cloud_owner
               LEFT JOIN bridge_release a ON a.question_id=r.question_id
               WHERE r.expires_at>%s AND r.remote_rejected_at IS NULL
                 AND a.delivered_at IS NULL
               ORDER BY r.admitted_at,r.question_id LIMIT 1""",(now,)
        ).fetchone()
        if row is None:
            return Action("claim"),INTERVAL
        if not row["enabled"] or not row["mapped"]:
            return Action("waiting"),INTERVAL
        if row["state"] in ("failed","expired","canceled"):
            kind="reject"
        elif row["acked_at"] is None:
            kind="ack"
        elif row["state"]=="succeeded":
            kind="answer"
        else:
            kind="waiting"
        return Action(kind,row["question_id"],row["fence"],row["task_id"]),INTERVAL


def defer(dsn,seconds,*,block=None):
    if type(seconds) is not int or not INTERVAL<=seconds<=86400:
        raise ValueError("invalid bridge cooldown")
    if block not in (None,"authentication","remote_conflict","local_integrity"):
        raise ValueError("invalid block reason")
    with locked(dsn) as (conn,_,now):
        conn.execute("""UPDATE bridge_control SET not_before=greatest(not_before,%s),
                        blocked_reason=coalesce(blocked_reason,%s)
                        WHERE singleton""",(now+seconds,block))


def record_rejection(dsn,action):
    with locked(dsn) as (conn,_,now):
        row=conn.execute(
            """UPDATE bridge_receipt r SET remote_rejected_at=coalesce(r.remote_rejected_at,%s)
               FROM work_task t WHERE r.question_id=%s AND r.fence=%s
               AND r.task_id=%s AND t.id=r.task_id AND r.expires_at>%s
               AND t.state IN ('failed','expired','canceled') RETURNING r.question_id""",
            (now,action.question_id,action.fence,action.task_id,now)
        ).fetchone()
        return row is not None
