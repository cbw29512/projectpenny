"""Trusted hourly admission adapter; only an already started private workshop."""
import logging

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.review import _valid_id
from penny.scheduler.storage_db import locked
from .store import LATEST
from .workshop_admission import _submit_locked
from .workshop_state import PREFIX

logger = logging.getLogger(__name__)


def plan_hour(dsn, *, reviewer_id, confirmed=False):
    """Record one decision per DB UTC hour; never run inference or approve work."""
    try:
        decision = authorize(Actor.ADMIN, Capability.REQUEST_WORKSHOP)
        if confirmed is not True or not _valid_id(reviewer_id) or not decision.allowed:
            return {"outcome": "denied", "replayed": False}
        with locked(dsn) as (conn, control, now):
            slot = now // 3600
            old = conn.execute(
                "SELECT * FROM hourly_plan WHERE hour_slot=%s", (slot,)
            ).fetchone()
            if old is not None:
                return dict(old, replayed=True)
            # Respect the durable runtime gates, not just scheduler admission.
            gate = conn.execute(
                "SELECT enabled,uncertain FROM inference_runtime WHERE singleton"
            ).fetchone()
            opportunity_id = task_id = None
            if control["paused"]:
                outcome = "paused"
            elif not gate or not gate["enabled"] or gate["uncertain"]:
                outcome = "blocked"
            elif conn.execute(
                """SELECT 1 FROM work_task WHERE state='running'
                   OR (state='queued' AND deadline>%s) LIMIT 1""", (now,)
            ).fetchone():
                outcome = "busy"
            else:
                # No automatic retries or revisions: any prior prototype task
                # means the Maker must review its outcome before another step.
                candidate = conn.execute(
                    "SELECT x.id FROM (" + LATEST + """) AS x
                    WHERE x.action='started' AND x.deadline>%s
                      AND x.category='digital_product'
                      AND NOT EXISTS (
                          SELECT 1 FROM workshop_task w WHERE w.opportunity_id=x.id
                      )
                    ORDER BY x.event_at,x.id LIMIT 1""", (now + 5,)
                ).fetchone()
                outcome = "no_eligible_work"
                if candidate:
                    opportunity_id = candidate["id"]
                    key = PREFIX + str(opportunity_id) + ":hourly-" + str(slot)
                    receipt = _submit_locked(
                        conn, control, now, opportunity_id, key, reviewer_id, decision
                    )
                    outcome = "admission_refused"
                    if receipt.status == "accept":
                        outcome, task_id = "scheduled", receipt.task_id
            row = conn.execute(
                """INSERT INTO hourly_plan
                   (hour_slot,recorded_at,outcome,opportunity_id,task_id)
                   VALUES (%s,%s,%s,%s,%s) RETURNING *""",
                (slot, now, outcome, opportunity_id, task_id)
            ).fetchone()
            return dict(row, replayed=False)
    except Exception as exc:
        logger.error("Hourly planner failed (%s)", type(exc).__name__)
        raise
