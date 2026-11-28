"""Restricted draft completion for every supervised intake route."""
import logging
from uuid import UUID

import psycopg

from penny.guardian.policy import validate_draft

logger=logging.getLogger(__name__)


class ScopedDraftCompletion:
    def __init__(self,cycle):
        if type(cycle) is not UUID or cycle.int==0:
            raise ValueError("invalid inference cycle")
        self._cycle=cycle

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
            if row is None or row[0] not in ("completed","canceled","refused"):
                raise RuntimeError("unexpected scoped completion")
            return row[0]=="completed"
        except Exception as exc:
            logger.error("Scoped draft completion failed (%s)",type(exc).__name__)
            raise
