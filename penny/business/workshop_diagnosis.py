"""Read-only historical workshop diagnosis; never retry or reconstruct authority."""
import logging
from hashlib import sha256

import psycopg
from psycopg.rows import dict_row

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.review import _valid_id
from .checklist import render_checklist

logger = logging.getLogger(__name__)


def diagnose(dsn, task_id):
    """Return bounded facts and possible explanations, not a fabricated cause."""
    try:
        if not _valid_id(task_id):
            raise ValueError("invalid workshop task")
        if not authorize(Actor.ADMIN, Capability.REVIEW_BUSINESS_EXPERIMENT).allowed:
            return None
        with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5) as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            conn.execute("SET LOCAL statement_timeout='5s'")
            row = conn.execute("""SELECT t.state,t.started_at,t.lease_until,
                    w.opportunity_id,o.status,o.result,o.finished_at,
                    a.task_id IS NOT NULL AS artifact_recorded
                FROM workshop_task w JOIN work_task t ON t.id=w.task_id
                LEFT JOIN task_outcome o ON o.task_id=t.id
                LEFT JOIN workshop_artifact a ON a.task_id=t.id
                WHERE w.task_id=%s AND t.member_id IS NULL""", (task_id,)).fetchone()
            if row is None:
                return None
            # Only timestamps and action codes; never return raw output or credentials.
            raw = row["result"]
            valid = None if raw is None else render_checklist(raw) is not None
            events = []
            count = 0
            if row["started_at"] is not None and row["finished_at"] is not None:
                events = conn.execute("""SELECT action,recorded_at FROM runtime_operator_event
                    WHERE recorded_at BETWEEN %s AND %s
                    ORDER BY recorded_at,id LIMIT 20""",
                    (row["started_at"],row["finished_at"])).fetchall()
                count = conn.execute("""SELECT count(*) AS n FROM runtime_operator_event
                    WHERE action='stop' AND recorded_at BETWEEN %s AND %s""",
                    (row["started_at"],row["finished_at"])).fetchone()["n"]
            if row["artifact_recorded"]:
                finding = "artifact_recorded_integrity_review_separate"
            elif row["status"] != "succeeded":
                finding = "no_successful_outcome"
            elif valid is False:
                finding = "stored_output_fails_current_validator"
            elif count:
                finding = "valid_output_stop_in_completion_window"
            else:
                finding = "valid_output_missing_artifact_cause_unverified"
            return {
                "task_id":str(task_id), "opportunity_id":str(row["opportunity_id"]),
                "task_state":row["state"], "artifact_recorded":row["artifact_recorded"],
                "started_at":row["started_at"], "finished_at":row["finished_at"],
                "output_sha256":None if raw is None else sha256(raw.encode("utf-8")).hexdigest(),
                "current_validator_passed":valid, "operator_events":events,
                "stop_events_in_window":count, "finding":finding,
                "cause_certified":False,
                "note":"Second-resolution audit timestamps cannot establish transaction order. No retry authorized."
            }
    except Exception as exc:
        logger.error("Workshop diagnosis failed (%s)", type(exc).__name__)
        raise
