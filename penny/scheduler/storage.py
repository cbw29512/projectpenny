"""Durable admission and exclusive claims; internal callers only."""
from uuid import UUID, uuid4

from penny.memory.task import INFORMED_PREFIX
from penny.business.draft_state import DRAFT_PREFIX
from penny.auth.member_scope import member_scope
from penny.memory.member_consent import active_consent

from .admit import BRIDGE_PREFIX, submit_locked
from .policy import next_task
from .storage_db import expire_waiting, locked, snapshot, tier_for
from .storage_state import Claim, Receipt


class TaskStore:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def submit(self, member: UUID | None, key: str, payload: str, *,
               _session_token=None, use_personal_memory=False) -> Receipt:
        # The caller must authenticate the member; None is internal-only.
        if (
            type(use_personal_memory) is not bool
            or (use_personal_memory and _session_token is None)
            or (_session_token is not None and member is not None)
            or (member is not None and not isinstance(member, UUID))
            or not isinstance(key, str) or not 1 <= len(key) <= 128
            or key.startswith((BRIDGE_PREFIX,DRAFT_PREFIX))
            or not isinstance(payload, str) or not 1 <= len(payload) <= 2000
            or not key.strip() or not payload.strip() or "\x00" in key or "\x00" in payload
        ):
            return Receipt("invalid")
        with member_scope(self.dsn,member,_session_token) as (conn,control,now,member):
            consent = active_consent(conn,member,now) if use_personal_memory else None
            if use_personal_memory and not consent:
                return Receipt("memory_consent_required")
            return submit_locked(conn,control,now,member,key,payload,consent)

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
            personal = row["member_id"] is not None and conn.execute(
                "SELECT 1 FROM member_recall_scope WHERE task_id=%s AND member_id=%s",
                (row["id"],row["member_id"]),
            ).fetchone() is not None
            return Claim(row["id"], fence, row["payload"], lease, informed, personal)

    def set_paused(self, paused: bool) -> None:
        if type(paused) is not bool:
            raise ValueError("paused must be boolean")
        with locked(self.dsn) as (conn, _, __):
            conn.execute("UPDATE scheduler_control SET paused=%s WHERE singleton", (paused,))
