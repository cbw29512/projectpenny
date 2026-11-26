"""Public-safe, private candidate of actual service availability. No inference."""
import logging
from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from penny.scheduler.rest_gate import rest_closed

logger = logging.getLogger(__name__)
SCHEMA = "penny-activity-v1"


def candidate_locked(conn, control, now):
    # This disclosure is deliberately coarse: no member IDs, prompts, titles,
    # task counts, private results, model details or financial assertions.
    unavailable = {"schema": SCHEMA, "status": "unavailable"}
    if not authorize(Actor.ADMIN, Capability.REVIEW_PROGRESS_SNAPSHOT).allowed:
        return unavailable
    gate = conn.execute("SELECT enabled,uncertain FROM inference_runtime WHERE singleton").fetchone()
    if gate is None:
        return unavailable
    active = conn.execute("SELECT lease_until FROM work_task WHERE state='running'").fetchone()
    closed = rest_closed(control, now)
    if active is not None and active["lease_until"] <= now:
        state = "blocked"
    elif control["paused"] or not gate["enabled"]:
        state = "paused"
    elif active is not None:
        state = "draining" if closed else "working"
    elif gate["uncertain"]:
        state = "blocked"
    elif closed:
        state = "off_duty"
    else:
        state = "idle"
    # Do not assert public chat availability merely because local work is idle.
    return {"schema":SCHEMA,"status":"reviewed","state":state,
            "sampled_at":now,"expires_at":now+15}


def browser_candidate(dsn):
    try:
        with locked(dsn) as (conn,control,now):
            return candidate_locked(conn,control,now)
    except Exception as exc:
        logger.error("Activity candidate unavailable (%s)",type(exc).__name__)
        return {"schema":SCHEMA,"status":"unavailable"}
