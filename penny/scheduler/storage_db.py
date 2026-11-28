"""Shared transactional state loading. No model or external effects."""
import logging
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from .state import QueueSnapshot, TaskSpec, Tier

logger = logging.getLogger(__name__)


@contextmanager
def locked(dsn):
    # One transaction serializes every queue mutation across processes.
    try:
        with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5) as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            conn.execute("SET LOCAL lock_timeout = '5s'")
            conn.execute("SET LOCAL statement_timeout = '10s'")
            control = conn.execute(
                "SELECT * FROM scheduler_control WHERE singleton FOR UPDATE"
            ).fetchone()
            if control is None:
                raise RuntimeError("scheduler migration missing")
            now = conn.execute(
                "SELECT floor(extract(epoch FROM clock_timestamp()))::bigint AS now"
            ).fetchone()["now"]
            yield conn, control, now
    except Exception as exc:
        # Never log payloads, connection strings or SQL error details.
        logger.error("Scheduler transaction failed (%s)", type(exc).__name__)
        raise


def tier_for(conn, member, now):
    if member is None:
        return None
    row = conn.execute(
        "SELECT tier FROM scheduler_entitlement WHERE member_id=%s AND valid_until>%s",
        (member, now),
    ).fetchone()
    return Tier(row["tier"]) if row else Tier.FREE


def expire_waiting(conn, now):
    conn.execute(
        """WITH expired AS (
            UPDATE work_task SET state='expired'
            WHERE state='queued' AND deadline<=%s RETURNING id
        ) INSERT INTO task_outcome
        SELECT id,'expired','deadline elapsed',%s,0 FROM expired""",
        (now, now),
    )


def spec(row):
    return TaskSpec(
        str(row["id"]), str(row["member_id"]) if row["member_id"] else None,
        Tier(row["tier_snapshot"]) if row["tier_snapshot"] is not None else None,
        row["submitted_at"], row["deadline"],
    )


def snapshot(conn, control, now):
    rows = conn.execute(
        "SELECT * FROM work_task WHERE state IN ('queued','running')"
    ).fetchall()
    usage = conn.execute(
        """SELECT
        COALESCE(sum(o.compute_seconds) FILTER (WHERE t.member_id IS NULL),0) AS business,
        COALESCE(sum(o.compute_seconds) FILTER (WHERE t.tier_snapshot>0),0) AS supporter,
        COALESCE(sum(o.compute_seconds) FILTER (WHERE t.tier_snapshot=0),0) AS free
        FROM task_outcome o JOIN work_task t ON t.id=o.task_id
        WHERE o.finished_at > %s""", (now - 86400,),
    ).fetchone()
    active = next((spec(r) for r in rows if r["state"] == "running"), None)
    last = control["last_member_id"]
    return QueueSnapshot(
        active=active, waiting=tuple(spec(r) for r in rows if r["state"] == "queued"),
        paused=control["paused"], last_member_id=str(last) if last else None,
        business_seconds=usage["business"], supporter_seconds=usage["supporter"],
        free_seconds=usage["free"],
    )
