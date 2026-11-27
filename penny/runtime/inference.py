"""Crash-safe inference cycle gate; never assert a stopped model automatically."""
import logging
from uuid import UUID

import psycopg

from penny.guardian.policy import identity_matches
from .claim_store import ScopedClaimStore
from .personal_recall import ScopedPersonalRecall
from penny.scheduler.worker import run_once, WorkerResult
from .inference_db import gate_call

logger=logging.getLogger(__name__)
LOCK_ID=724390581215032


def inference_tick(dsn,brain):
    try:
        if not identity_matches():
            return "paused"
        # Session advisory lock serializes supported worker invocations.
        # DB reservation survives process death and is distinct from a task fence.
        with psycopg.connect(dsn,autocommit=True,connect_timeout=5) as guard:
            guard.execute("SET statement_timeout='5s'")
            if not guard.execute("SELECT pg_try_advisory_lock(%s)",(LOCK_ID,)).fetchone()[0]:
                return "busy"
            row=gate_call(dsn,"begin")
            status,token=row["status"],row["token"]
            if status in ("paused","blocked") and token is None:
                return status
            if status!="reserved" or type(token) is not UUID or token.int==0:
                raise RuntimeError("invalid inference cycle reservation")
            # No transaction is held across model execution.
            result=run_once(ScopedClaimStore(dsn,token),brain,personal_recall=ScopedPersonalRecall(token))
            outcome=result.value if type(result) is WorkerResult else "blocked"
            finished=gate_call(dsn,"finish",(token,outcome))["status"]
            if finished not in ("idle","completed","blocked"):
                raise RuntimeError("invalid inference cycle outcome")
            return finished
    except Exception as exc:
        logger.error("Inference runtime stopped (%s)",type(exc).__name__)
        return "blocked"
