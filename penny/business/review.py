"""Administrator-only transitions, exact evidence and one active experiment."""
import logging
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked
from .state import Action,MAX_COUNT
from .store import LATEST

logger=logging.getLogger(__name__)


def advance(dsn,opportunity_id,*,action,expected_proposal_sha256,
            evidence_ref,evidence,reviewer_id,confirmed,
            observed_at=None,measured_count=None):
    """Record a human-reviewed transition, not an execution instruction."""
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT)
        if not decision.allowed:
            return False
        if (not _valid_id(opportunity_id) or not _valid_id(reviewer_id)
                or type(action) is not Action or not _valid_ref(evidence_ref)
                or type(expected_proposal_sha256) is not str or confirmed is not True):
            raise ValueError("invalid experiment review")
        if action is Action.MEASURE:
            if (type(observed_at) is not int or type(measured_count) is not int
                    or not 0<=measured_count<=MAX_COUNT):
                raise ValueError("invalid observation")
        elif observed_at is not None or measured_count is not None:
            raise ValueError("unexpected measurement")
        key=uuid4()
        mark=fingerprint(key,evidence)
        with locked(dsn) as (conn,control,now):
            row=conn.execute(LATEST+" WHERE o.id=%s",(opportunity_id,)).fetchone()
            if row is None or row["evidence_sha256"]!=expected_proposal_sha256:
                return False
            current=row["action"]
            deadline=None
            if action in (Action.APPROVE,Action.REJECT):
                if current is not None or row["review_until"]<=now:
                    return False
            elif action is Action.START:
                if current!="approved" or row["review_until"]<=now or control["paused"]:
                    return False
                if conn.execute("SELECT 1 FROM ("+LATEST+
                    ") AS x WHERE action='started' LIMIT 1").fetchone():
                    return False
                deadline=now+row["duration_seconds"]
            elif action is Action.STOP:
                if current not in ("approved","started"):
                    return False
            elif action is Action.MEASURE:
                if (current!="started" or not row["event_at"]<=observed_at<row["deadline"]
                        or observed_at>now):
                    return False
            conn.execute("""INSERT INTO business_experiment_event
                (id,opportunity_id,action,reviewer_id,recorded_at,deadline,
                 observed_at,measured_count,evidence_ref,evidence_sha256,evidence_size,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (key,opportunity_id,action.value,reviewer_id,now,deadline,
                 observed_at,measured_count,evidence_ref,mark.digest,mark.byte_count,
                 decision.policy_version))
            return True
    except Exception as exc:
        logger.error("Business experiment transition refused (%s)",type(exc).__name__)
        raise
