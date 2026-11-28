"""Persistent bridge scheduling, separate from the inference transaction."""
import logging
from contextlib import contextmanager

import psycopg

from penny.guardian.policy import identity_matches
from .reply_db import reply_call
from .receipts import valid_id
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
    if not identity_matches():
        return Action("paused"),INTERVAL
    row=reply_call(dsn,"reserve",())
    if row is None or row["kind"] not in (
            "paused","cooldown","waiting","claim","ack","answer","reject"):
        raise RuntimeError("invalid mailbox reservation")
    ids=(row["question_id"],row["fence"],row["task_id"])
    if (type(row["delay"]) is not int or row["delay"]<1
            or (row["kind"] in ("ack","answer","reject") and not all(map(valid_id,ids)))
            or (row["kind"] in ("paused","cooldown","claim") and any(x is not None for x in ids))
            or (row["kind"]=="waiting" and not (all(x is None for x in ids) or all(map(valid_id,ids))))):
        raise RuntimeError("invalid mailbox action")
    return Action(row["kind"],*ids),row["delay"]


def defer(dsn,seconds,*,block=None):
    if type(seconds) is not int or not INTERVAL<=seconds<=86400:
        raise ValueError("invalid bridge cooldown")
    if block not in (None,"authentication","remote_conflict","local_integrity"):
        raise ValueError("invalid block reason")
    row=reply_call(dsn,"defer",(seconds,block))
    if row is None or row["recorded"] is not True:
        raise RuntimeError("mailbox cooldown not recorded")


def record_rejection(dsn,action):
    if (type(action) is not Action or action.kind!="reject" or not all(
            valid_id(x) for x in (action.question_id,action.fence,action.task_id))):
        return False
    row=reply_call(dsn,"reject",(action.question_id,action.fence,action.task_id))
    return row is not None and row["recorded"] is True
