"""Bounded candidate timeline; no public endpoint, identity or raw source data."""
import logging
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.scheduler.storage_db import locked
from .timeline_state import SCHEMA,MAX_EVENTS,public_event

logger=logging.getLogger(__name__)


def recent(dsn,*,limit=MAX_EVENTS):
    try:
        if type(limit) is not int or not 1<=limit<=MAX_EVENTS:
            raise ValueError("invalid timeline limit")
        if not authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT).allowed:
            return {"schema":SCHEMA,"status":"unavailable","events":[]}
        with locked(dsn) as (conn,_,now):
            rows=conn.execute("""SELECT e.kind,e.occurred_at,s.recorded_at AS corrected_at
                FROM progress_timeline_event e LEFT JOIN progress_timeline_suppression s
                ON s.event_id=e.id
                ORDER BY coalesce(s.recorded_at,e.occurred_at) DESC,e.sequence DESC LIMIT %s""",
                (limit,)).fetchall()
            events=[]
            for row in rows:
                corrected=row["corrected_at"]
                at=corrected if corrected is not None else row["occurred_at"]
                if at>now:
                    raise ValueError("future timeline event")
                events.append(public_event("corrected" if corrected is not None else row["kind"],at))
            return {"schema":SCHEMA,"status":"reviewed" if events else "unavailable","events":events}
    except Exception as exc:
        logger.error("Timeline read unavailable (%s)",type(exc).__name__)
        return {"schema":SCHEMA,"status":"unavailable","events":[]}
