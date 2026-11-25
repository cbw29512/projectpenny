"""Durable admission and exclusive claims; internal callers only."""
from uuid import UUID, uuid4

from penny.memory.task import INFORMED_PREFIX

from .policy import admission, next_task
from .state import Admission, TaskSpec
from .storage_db import expire_waiting, locked, snapshot, tier_for
from .storage_state import Claim, Receipt


class TaskStore:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def submit(self, member: UUID | None, key: str, payload: str) -> Receipt:
        # The caller must authenticate the member; None is internal-only.
        if (
            (member is not None and not isinstance(member, UUID))
            or not isinstance(key, str) or not 1 <= len(key) <= 128
            or not isinstance(payload, str) or not 1 <= len(payload) <= 2000
            or not key.strip() or not payload.strip() or "\x00" in key or "\x00" in payload
        ):
            return Receipt("invalid")
        with locked(self.dsn) as (conn, control, now):
            previous = conn.execute(
                """SELECT id,payload FROM work_task
                WHERE member_id IS NOT DISTINCT FROM %s::uuid AND idempotency_key=%s""",
                (member, key),
            ).fetchone()
            if previous:
                if previous["payload"] != payload:
                    return Receipt("idempotency_conflict")
                return Receipt("accept", previous["id"], True)
            expire_waiting(conn, now)
            tier = tier_for(conn, member, now)
            task_id = uuid4()
            deadline = now + (86400 if member is None else 3600)
            task = TaskSpec(str(task_id), str(member) if member else None, tier, now, deadline)
            decision = admission(snapshot(conn, control, now), task, now)
            if decision != Admission.ACCEPT:
                return Receipt(decision.value)
            conn.execute(
                """INSERT INTO work_task
                (id,member_id,tier_snapshot,idempotency_key,payload,submitted_at,deadline,state)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'queued')""",
                (task_id, member, int(tier) if tier is not None else None, key, payload, now, deadline),
            )
            return Receipt("accept", task_id)

    def claim(self) -> Claim | None:
        with locked(self.dsn) as (conn, control, now):
            expire_waiting(conn, now)
            # Changed entitlements cannot silently enter another reserved class.
            rows = conn.execute(
                "SELECT id,member_id,tier_snapshot FROM work_task WHERE state='queued'"
            ).fetchall()
            for row in rows:
                tier = tier_for(conn, row["member_id"], now)
                if tier != row["tier_snapshot"]:
                    conn.execute("UPDATE work_task SET state='canceled' WHERE id=%s", (row["id"],))
                    conn.execute(
                        "INSERT INTO task_outcome VALUES (%s,'canceled','entitlement changed',%s,0)",
                        (row["id"], now),
                    )
            chosen = next_task(snapshot(conn, control, now), now)
            if chosen is None:
                return None
            fence = uuid4()
            lease = min(chosen.expires_at, now + (900 if chosen.member_id is None else 120))
            row = conn.execute(
                """UPDATE work_task SET state='running',fence=%s,started_at=%s,lease_until=%s
                WHERE id=%s AND state='queued' RETURNING id,payload,member_id,idempotency_key""",
                (fence, now, lease, UUID(chosen.task_id)),
            ).fetchone()
            if row is None:
                raise RuntimeError("claimed task disappeared")
            informed = (row["member_id"] is None and
                        row["idempotency_key"].startswith(INFORMED_PREFIX))
            return Claim(row["id"], fence, row["payload"], lease, informed)

    def set_paused(self, paused: bool) -> None:
        if type(paused) is not bool:
            raise ValueError("paused must be boolean")
        with locked(self.dsn) as (conn, _, __):
            conn.execute("UPDATE scheduler_control SET paused=%s WHERE singleton", (paused,))
