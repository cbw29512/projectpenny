"""Public-safe, private candidate of actual service availability. No inference."""
import logging
from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from penny.scheduler.rest_gate import rest_closed
from .activity_db import activity_call

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
    return classify(control,gate,active["lease_until"] if active else None,now)


def classify(control,gate,active_lease,now):
    closed = rest_closed(control, now)
    if active_lease is not None and active_lease <= now:
        state = "blocked"
    elif active_lease is not None:
        # An emergency pause does not prove the in-flight worker stopped.
        state = "draining" if closed or control["paused"] or not gate["enabled"] else "working"
    elif gate["uncertain"]:
        state = "blocked"
    elif control["paused"] or not gate["enabled"]:
        state = "paused"
    elif closed:
        state = "off_duty"
    else:
        state = "idle"
    return {"schema":SCHEMA,"status":"reviewed","state":state,
            "sampled_at":now,"expires_at":now+15}


def browser_candidate(dsn):
    try:
        if not authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT).allowed:
            return {"schema":SCHEMA,"status":"unavailable"}
        row=activity_call(dsn,"inputs")
        if (set(row)!={"paused","rest_enabled","inference_enabled","uncertain","active_lease","sampled_at"}
                or any(type(row[k]) is not bool for k in
                       ("paused","rest_enabled","inference_enabled","uncertain"))
                or type(row["sampled_at"]) is not int
                or (row["active_lease"] is not None and type(row["active_lease"]) is not int)):
            raise ValueError("invalid activity input")
        return classify(row,{"enabled":row["inference_enabled"],"uncertain":row["uncertain"]},
                        row["active_lease"],row["sampled_at"])
    except Exception as exc:
        logger.error("Activity candidate unavailable (%s)",type(exc).__name__)
        return {"schema":SCHEMA,"status":"unavailable"}
