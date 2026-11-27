"""Claim-only repository for the supervised inference worker."""
import logging
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from penny.scheduler.storage_state import Claim

logger=logging.getLogger(__name__)


class ScopedClaimStore:
    def __init__(self,dsn,cycle):
        if type(cycle) is not UUID or cycle.int==0:
            raise ValueError("invalid inference cycle")
        self.dsn=dsn
        self._cycle=cycle

    def claim(self):
        try:
            with psycopg.connect(self.dsn,row_factory=dict_row,connect_timeout=5) as conn:
                conn.execute("SET LOCAL lock_timeout='5s'")
                conn.execute("SET LOCAL statement_timeout='10s'")
                rows=conn.execute("SELECT * FROM penny_inference_claim(%s)",(self._cycle,)).fetchall()
                if not rows:
                    return None
                if len(rows)!=1:
                    raise RuntimeError("unexpected inference claim count")
                row=rows[0]
                if (set(row)!={"task_id","fence","payload","lease_until","memory_enabled","personal_memory_enabled"}
                        or any(type(row[k]) is not UUID or row[k].int==0 for k in ("task_id","fence"))
                        or type(row["payload"]) is not str or not row["payload"].strip()
                        or len(row["payload"])>2000 or "\x00" in row["payload"]
                        or type(row["lease_until"]) is not int or row["lease_until"]<=0
                        or type(row["memory_enabled"]) is not bool or type(row["personal_memory_enabled"]) is not bool
                        or (row["memory_enabled"] and row["personal_memory_enabled"])):
                    raise ValueError("invalid scoped task claim")
                return Claim(**row)
        except Exception as exc:
            logger.error("Inference claim refused (%s)",type(exc).__name__)
            raise
