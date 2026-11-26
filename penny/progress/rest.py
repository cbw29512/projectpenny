"""Trusted private rest review and browser candidate; no publication."""
import logging
import os
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from penny.scheduler.rest_gate import rest_closed
from .rest_schedule import POLICY_VERSION, window_at

logger = logging.getLogger(__name__)
SCHEMA = "penny-rest-v1"


def configure(dsn, enabled, *, confirmed=False):
    """Local authenticated operator only; never clears manual/runtime controls."""
    try:
        if type(enabled) is not bool or confirmed is not True:
            return False
        if not authorize(Actor.ADMIN, Capability.REVIEW_VIRTUAL_WORLD).allowed:
            return False
        with locked(dsn) as (conn, control, now):
            if window_at(now) is None:
                return False
            conn.execute("UPDATE scheduler_control SET rest_enabled=%s WHERE singleton",
                         (enabled,))
            conn.execute("""INSERT INTO rest_policy_review
                (id,enabled,policy_version,reviewed_at,operator_uid)
                VALUES (%s,%s,%s,%s,%s)""",
                         (uuid4(),enabled,POLICY_VERSION,now,os.getuid()))
            return True
    except Exception as exc:
        logger.error("Rest policy review failed (%s)", type(exc).__name__)
        raise


def candidate_locked(conn, control, now):
    """A conservative, short-lived snapshot based on actual locked state."""
    unavailable = {"schema":SCHEMA,"status":"unavailable"}
    if not authorize(Actor.ADMIN, Capability.REVIEW_VIRTUAL_WORLD).allowed:
        return unavailable
    window = window_at(now)
    if control["rest_enabled"] is not True or window is None:
        return unavailable
    gate = conn.execute("SELECT enabled,uncertain FROM inference_runtime WHERE singleton").fetchone()
    active = conn.execute("SELECT lease_until FROM work_task WHERE state='running'").fetchone()
    if gate is None:
        return unavailable
    closed = rest_closed(control,now)
    state, wake = "awake", None
    # Unknown inference is never called asleep. A live fenced task is still
    # draining (not a claim of GPU idleness); expired fences need recovery.
    if active and active["lease_until"] <= now:
        state = "blocked"
    elif active and closed and not control["paused"] and gate["enabled"]:
        state = "draining"
    elif control["paused"] or not gate["enabled"] or gate["uncertain"]:
        state = "blocked"
    elif closed:
        state = "asleep"
        wake = window.next_transition
    return {"schema":SCHEMA,"status":"reviewed","policy":POLICY_VERSION,
            "state":state,"sampled_at":now,"expires_at":min(now+60,window.next_transition),
            "wake_at":wake,"gate_closed":closed,"active":active is not None}


def browser_candidate(dsn):
    try:
        with locked(dsn) as (conn,control,now):
            return candidate_locked(conn,control,now)
    except Exception as exc:
        logger.error("Rest projection unavailable (%s)",type(exc).__name__)
        return {"schema":SCHEMA,"status":"unavailable"}
