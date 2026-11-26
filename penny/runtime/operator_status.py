"""Private operational status; no model inference or conversation disclosure."""
from penny.guardian.policy import identity_matches
from penny.scheduler.storage_db import locked
from penny.progress.rest import candidate_locked


def status(dsn):
    with locked(dsn) as (conn,control,now):
        inference=conn.execute("SELECT * FROM inference_runtime WHERE singleton").fetchone()
        bridge=conn.execute("SELECT * FROM bridge_control WHERE singleton").fetchone()
        if inference is None or bridge is None:
            raise RuntimeError("runtime migrations missing")
        active=conn.execute("""SELECT id,fence,lease_until FROM work_task
                              WHERE state='running'""").fetchone()
        counts=conn.execute("""SELECT state,count(*) AS n FROM work_task
                              GROUP BY state""").fetchall()
        return {
            "identity_valid":identity_matches(),
            "scheduler_paused":control["paused"],
            "rest_enabled":control["rest_enabled"],
            "rest":candidate_locked(conn,control,now),
            "inference_enabled":inference["enabled"],
            "inference_uncertain":inference["uncertain"],
            "inference_last_result":inference["last_result"],
            "bridge_enabled":bridge["enabled"],
            "bridge_block":bridge["blocked_reason"],
            "bridge_cooldown_seconds":max(0,bridge["not_before"]-now),
            "active":None if active is None else {
                "task_id":str(active["id"]),"fence":str(active["fence"]),
                "lease_remaining_seconds":max(0,active["lease_until"]-now),
            },
            "task_counts":{row["state"]:row["n"] for row in counts},
        }
