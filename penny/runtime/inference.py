"""Crash-safe inference cycle gate; never assert a stopped model automatically."""
import logging

import psycopg

from penny.guardian.policy import identity_matches
from penny.scheduler.storage_db import locked
from penny.scheduler.storage import TaskStore
from penny.scheduler.worker import run_once, WorkerResult

logger = logging.getLogger(__name__)
LOCK_ID = 724390581215032


def inference_tick(dsn, brain):
    try:
        # Session lock prevents overlapping service invocations; the durable
        # uncertain marker survives a process death or lost DB connection.
        with psycopg.connect(dsn,autocommit=True,connect_timeout=5) as guard:
            guard.execute("SET statement_timeout='5s'")
            if not guard.execute("SELECT pg_try_advisory_lock(%s)",(LOCK_ID,)).fetchone()[0]:
                return "busy"
            with locked(dsn) as (conn,control,now):
                gate=conn.execute("SELECT * FROM inference_runtime WHERE singleton FOR UPDATE").fetchone()
                if (gate is None or not gate["enabled"] or control["paused"]
                        or not identity_matches()):
                    return "paused"
                if gate["uncertain"]:
                    return "blocked"
                if conn.execute("SELECT 1 FROM work_task WHERE state='running'").fetchone():
                    conn.execute("UPDATE inference_runtime SET uncertain=true,last_result='interrupted' WHERE singleton")
                    return "blocked"
                conn.execute("""UPDATE inference_runtime SET uncertain=true,
                             last_started=%s,last_result='interrupted' WHERE singleton""",(now,))
            # Do not hold the scheduler transaction across model execution.
            result=run_once(TaskStore(dsn),brain)
            with locked(dsn) as (conn,_,now):
                active=conn.execute("SELECT 1 FROM work_task WHERE state='running'").fetchone()
                safe=result in (WorkerResult.IDLE,WorkerResult.COMPLETED) and active is None
                conn.execute("""UPDATE inference_runtime SET uncertain=%s,
                    last_finished=%s,last_result=%s WHERE singleton""",
                    (not safe,now,result.value if safe else "blocked"))
            return result.value if safe else "blocked"
    except Exception as exc:
        logger.error("Inference runtime stopped (%s)",type(exc).__name__)
        return "blocked"
