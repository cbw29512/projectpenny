"""Scoped personal preference reader for the supervised inference worker."""
import logging
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.member_state import MemberPreference,MAX_PREFERENCE_CHARS
from penny.memory.member_recall import MAX_PERSONAL_RECALL

logger=logging.getLogger(__name__)


class ScopedPersonalRecall:
    def __init__(self,cycle):
        if type(cycle) is not UUID or cycle.int==0:
            raise ValueError("invalid inference cycle")
        self._cycle=cycle

    def __call__(self,dsn,task_id,fence):
        try:
            if any(type(v) is not UUID or v.int==0 for v in (task_id,fence)):
                return ()
            if not authorize(Actor.WORKER,Capability.RECALL_MEMBER_MEMORY).allowed:
                return ()
            with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=5) as conn:
                conn.execute("SET LOCAL lock_timeout='5s'")
                conn.execute("SET LOCAL statement_timeout='10s'")
                rows=conn.execute("SELECT * FROM penny_inference_personal_recall(%s,%s,%s)",
                                  (self._cycle,task_id,fence)).fetchall()
                if len(rows)>MAX_PERSONAL_RECALL:
                    raise ValueError("personal recall count exceeded")
                items=[]
                seen=set()
                for row in rows:
                    if (set(row)!={"id","preference"} or type(row["id"]) is not UUID
                            or row["id"].int==0 or row["id"] in seen
                            or type(row["preference"]) is not str or not row["preference"].strip()
                            or len(row["preference"])>MAX_PREFERENCE_CHARS or "\x00" in row["preference"]):
                        raise ValueError("invalid personal recall result")
                    seen.add(row["id"])
                    items.append(MemberPreference(row["id"],row["preference"]))
                return tuple(items)
        except Exception as exc:
            logger.error("Scoped personal recall refused (%s)",type(exc).__name__)
            raise
