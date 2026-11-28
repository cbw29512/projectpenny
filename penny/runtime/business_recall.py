"""Scoped reviewed-business memory reader for supervised inference."""
import logging
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.review_state import ReviewedMemory,MAX_RECALL_CHARS,MAX_RECALL_RECORDS
from penny.memory.state import MemoryKind,MAX_CONTENT

logger=logging.getLogger(__name__)


class ScopedBusinessRecall:
    def __init__(self,cycle):
        if type(cycle) is not UUID or cycle.int==0:
            raise ValueError("invalid inference cycle")
        self._cycle=cycle

    def __call__(self,dsn,task_id,fence):
        try:
            if any(type(v) is not UUID or v.int==0 for v in (task_id,fence)):
                return ()
            if not authorize(Actor.WORKER,Capability.RECALL_BUSINESS_MEMORY).allowed:
                return ()
            with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=5) as conn:
                conn.execute("SET LOCAL lock_timeout='5s'")
                conn.execute("SET LOCAL statement_timeout='10s'")
                rows=conn.execute("SELECT * FROM penny_inference_business_recall(%s,%s,%s)",
                                  (self._cycle,task_id,fence)).fetchall()
                if len(rows)>MAX_RECALL_RECORDS:
                    raise ValueError("business recall count exceeded")
                items=[]
                seen=set()
                remaining=MAX_RECALL_CHARS
                for row in rows:
                    if set(row)!={"source_task_id","kind","content"}:
                        raise ValueError("invalid business recall fields")
                    source,kind,content=row["source_task_id"],row["kind"],row["content"]
                    if (type(source) is not UUID or source.int==0 or source in seen
                            or type(kind) is not str or type(content) is not str
                            or not content.strip() or "\x00" in content
                            or len(content)>min(remaining,MAX_CONTENT)):
                        raise ValueError("invalid business recall record")
                    MemoryKind(kind)
                    seen.add(source)
                    remaining-=len(content)
                    items.append(ReviewedMemory(source,kind,content))
                return tuple(items)
        except Exception as exc:
            logger.error("Scoped business recall refused (%s)",type(exc).__name__)
            raise
