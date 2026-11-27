"""Scoped ordinary draft completion with explicit transitional intake path."""
import logging
from uuid import UUID

import psycopg

from penny.guardian.policy import validate_draft
from penny.scheduler.outcomes import complete

logger=logging.getLogger(__name__)


class ScopedDraftCompletion:
    def __init__(self,cycle,*,allow_legacy_specialized=False):
        if type(cycle) is not UUID or cycle.int==0:
            raise ValueError("invalid inference cycle")
        if type(allow_legacy_specialized) is not bool:
            raise ValueError("invalid completion mode")
        self._cycle=cycle
        self._legacy=allow_legacy_specialized

    def __call__(self,dsn,task_id,fence,*,success,result):
        try:
            if (success is not True or any(type(v) is not UUID or v.int==0
                    for v in (task_id,fence)) or not validate_draft(result).allowed):
                return False
            with psycopg.connect(dsn,connect_timeout=5) as conn:
                conn.execute("SET LOCAL lock_timeout='5s'")
                conn.execute("SET LOCAL statement_timeout='10s'")
                row=conn.execute("SELECT penny_inference_complete_draft(%s,%s,%s,%s)",
                                 (self._cycle,task_id,fence,result)).fetchone()
            if row is None or row[0] not in ("completed","canceled","refused","specialized"):
                raise RuntimeError("unexpected scoped completion")
            if row[0]=="specialized" and self._legacy:
                # Explicit transitional compatibility only. Never retry on
                # denied privileges, refusal, transport or uncertain outcome.
                return complete(dsn,task_id,fence,success=True,result=result)
            return row[0]=="completed"
        except Exception as exc:
            logger.error("Scoped draft completion failed (%s)",type(exc).__name__)
            raise
