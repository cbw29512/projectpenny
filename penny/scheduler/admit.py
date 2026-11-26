"""Shared admission under the existing scheduler transaction lock."""
from uuid import uuid4

from penny.guardian.policy import identity_matches
from .policy import admission
from .quotas import member_budget
from .state import Admission, TaskSpec
from .storage_db import expire_waiting, snapshot, tier_for
from .storage_state import Receipt
from .rest_gate import rest_closed

BRIDGE_PREFIX = "bridge:"


def submit_locked(conn,control,now,member,key,payload,consent=None,*,deadline_cap=None):
    # Caller already authenticated ownership and holds scheduler_control lock.
    previous = conn.execute(
        """SELECT t.id,t.payload,s.epoch FROM work_task t
        LEFT JOIN member_recall_scope s ON s.task_id=t.id
        WHERE t.member_id IS NOT DISTINCT FROM %s::uuid AND t.idempotency_key=%s""",
        (member, key),
    ).fetchone()
    if previous:
        if previous["payload"] != payload or previous["epoch"] != (consent["epoch"] if consent else None):
            return Receipt("idempotency_conflict")
        return Receipt("accept", previous["id"], True)
    if not identity_matches():
        return Receipt("identity_unavailable")
    expire_waiting(conn, now)
    if rest_closed(control, now):
        return Receipt("resting")
    tier = tier_for(conn, member, now)
    task_id = uuid4()
    deadline = now + (86400 if member is None else 3600)
    if deadline_cap is not None:
        deadline = min(deadline, deadline_cap)
    if deadline <= now:
        return Receipt("expired")
    task = TaskSpec(str(task_id), str(member) if member else None, tier, now, deadline)
    decision = admission(snapshot(conn, control, now), task, now)
    if decision != Admission.ACCEPT:
        return Receipt(decision.value)
    rejection = member_budget(conn,member,tier,now)
    if rejection:
        return Receipt(rejection)
    conn.execute(
        """INSERT INTO work_task
        (id,member_id,tier_snapshot,idempotency_key,payload,submitted_at,deadline,state)
        VALUES (%s,%s,%s,%s,%s,%s,%s,'queued')""",
        (task_id, member, int(tier) if tier is not None else None, key, payload, now, deadline),
    )
    if consent:
        conn.execute("INSERT INTO member_recall_scope VALUES (%s,%s,%s)",
                     (task_id,member,consent["epoch"]))
    return Receipt("accept", task_id)
