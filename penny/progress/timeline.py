"""Reviewed terminal business history, local-only candidate read model."""
import logging
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked
from penny.vault.state import JournalReceipt
from .timeline_state import SCHEMA,MAX_EVENTS,MAX_TIME,public_event,source_digest

logger=logging.getLogger(__name__)


def _source(conn,event_id,now):
    row=conn.execute("""SELECT e.id,e.action,e.recorded_at,e.observed_at,
        e.measured_count,e.evidence_sha256,o.target
        FROM business_experiment_event e JOIN business_opportunity o
        ON o.id=e.opportunity_id WHERE e.id=%s""",(event_id,)).fetchone()
    if not row or row["action"] not in ("measured","stopped","rejected"):
        return None
    if row["action"]=="measured":
        kind="target_met" if row["measured_count"]>=row["target"] else "target_missed"
        occurred=row["observed_at"]
    else:
        kind="experiment_"+row["action"]
        occurred=row["recorded_at"]
    if not 0<occurred<=row["recorded_at"]<=now<=MAX_TIME:
        return None
    data={**row,"id":str(row["id"])}
    return kind,occurred,source_digest(data)


def preview_event(dsn,event_id):
    try:
        if not _valid_id(event_id):
            raise ValueError("invalid event")
        if not authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            source=_source(conn,event_id,now)
            if source is None:
                return None
            kind,occurred,digest=source
            return {"event":public_event(kind,occurred),"source_digest":digest}
    except Exception as exc:
        logger.error("Timeline preview refused (%s)",type(exc).__name__)
        raise


def record_event(dsn,event_id,*,source_ref,expected_digest,reviewer_id,
                 evidence_ref,evidence,confirmed):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT)
        if not decision.allowed:
            return None
        if (confirmed is not True or not _valid_id(event_id) or not _valid_id(reviewer_id)
                or not _valid_ref(source_ref) or not _valid_ref(evidence_ref)
                or type(expected_digest) is not str or len(expected_digest)!=64):
            raise ValueError("invalid timeline review")
        key=uuid4()
        mark=fingerprint(key,evidence)
        fields=("experiment_event_id","source_sha256","reviewer_id",
                "evidence_ref","evidence_sha256","evidence_size")
        values=(event_id,expected_digest,reviewer_id,evidence_ref,mark.digest,mark.byte_count)
        with locked(dsn) as (conn,_,now):
            old=conn.execute("SELECT * FROM progress_timeline_event WHERE source_ref=%s",
                             (source_ref,)).fetchone()
            if old:
                if tuple(old[k] for k in fields)!=values:
                    raise ValueError("conflicting timeline review")
                return JournalReceipt(old["id"],True)
            source=_source(conn,event_id,now)
            if source is None or source[2]!=expected_digest:
                return None
            if conn.execute("SELECT 1 FROM progress_timeline_event WHERE experiment_event_id=%s",
                            (event_id,)).fetchone():
                return None
            kind,occurred,_=source
            conn.execute("""INSERT INTO progress_timeline_event
                (id,source_ref,experiment_event_id,source_sha256,reviewer_id,evidence_ref,
                 evidence_sha256,evidence_size,kind,occurred_at,recorded_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (key,source_ref,*values,kind,occurred,now,decision.policy_version))
            return JournalReceipt(key)
    except Exception as exc:
        logger.error("Timeline review refused (%s)",type(exc).__name__)
        raise


def suppress(dsn,event_id,*,reviewer_id,evidence_ref,evidence,confirmed):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT)
        if not decision.allowed:
            return False
        if (confirmed is not True or not _valid_id(event_id) or not _valid_id(reviewer_id)
                or not _valid_ref(evidence_ref)):
            raise ValueError("invalid timeline correction")
        mark=fingerprint(event_id,evidence)
        with locked(dsn) as (conn,_,now):
            if not conn.execute("SELECT 1 FROM progress_timeline_event WHERE id=%s",(event_id,)).fetchone():
                return False
            return conn.execute("""INSERT INTO progress_timeline_suppression VALUES
                (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(event_id) DO NOTHING RETURNING event_id""",
                (event_id,reviewer_id,now,evidence_ref,mark.digest,mark.byte_count,
                 decision.policy_version)).fetchone() is not None
    except Exception as exc:
        logger.error("Timeline correction refused (%s)",type(exc).__name__)
        raise
