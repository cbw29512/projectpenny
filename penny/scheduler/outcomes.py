"""Fenced completion and conservative supervisor recovery."""
from uuid import UUID

from penny.memory.intake import stage_from_review
from penny.memory.maintenance import stage_maintenance

from .storage_db import locked


def _finalize(conn, row, status, result, now):
    # Wall time is a provisional compute proxy. Cap it at the lease.
    seconds = max(1, min(now, row["lease_until"]) - row["started_at"])
    conn.execute("UPDATE work_task SET state=%s WHERE id=%s", (status, row["id"]))
    conn.execute(
        "INSERT INTO task_outcome VALUES (%s,%s,%s,%s,%s)",
        (row["id"], status, result, now, seconds),
    )
    conn.execute(
        "UPDATE scheduler_control SET last_member_id=%s WHERE singleton",
        (row["member_id"],),
    )


def _running(conn, task_id, fence):
    return conn.execute(
        "SELECT * FROM work_task WHERE id=%s AND fence=%s AND state='running'",
        (task_id, fence),
    ).fetchone()


def complete(dsn: str, task_id: UUID, fence: UUID, *, success: bool, result: str) -> bool:
    if (
        type(success) is not bool or not isinstance(result, str)
        or len(result) > 16000 or "\x00" in result
        or (success and not result.strip())
    ):
        raise ValueError("invalid completion")
    with locked(dsn) as (conn, _, now):
        row = _running(conn, task_id, fence)
        if not row or now >= row["lease_until"]:
            return False
        _finalize(conn, row, "succeeded" if success else "failed", result, now)
        if success:
            # Candidate and its fenced source outcome commit together or not at all.
            stage_from_review(conn, row, result)
            stage_maintenance(conn, row, result, now)
        return True


def recover_expired(
    dsn: str, task_id: UUID, fence: UUID, *, worker_isolated: bool
) -> bool:
    """Supervisor ONLY: assert isolation after confirming old work is stopped.

    This is an attestation, not a process-kill mechanism. Never auto-steal a lease.
    """
    if worker_isolated is not True:
        return False
    with locked(dsn) as (conn, _, now):
        row = _running(conn, task_id, fence)
        if not row or now < row["lease_until"]:
            return False
        _finalize(conn, row, "failed", "worker lost; safe stop confirmed", now)
        return True
