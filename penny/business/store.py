"""Immutable private experiment proposals, no model or member mutation."""
import logging
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked
from penny.vault.state import JournalReceipt
from .state import Category,Metric,MAX_REVIEW,MAX_OPEN

logger=logging.getLogger(__name__)

LATEST="""SELECT o.*,e.action,e.recorded_at AS event_at,e.deadline,e.measured_count
 FROM business_opportunity o LEFT JOIN LATERAL (
   SELECT action,recorded_at,deadline,measured_count FROM business_experiment_event
   WHERE opportunity_id=o.id ORDER BY sequence DESC LIMIT 1
 ) e ON true"""


def _text(s,limit):
    return type(s) is str and 1<=len(s)<=limit and bool(s.strip()) and not any(
        ord(c)<32 or 0xD800<=ord(c)<=0xDFFF for c in s)


def stage(dsn,*,source_ref,category,title,hypothesis,metric,target,duration_seconds,
          additional_cash_cents,evidence_ref,evidence,reviewer_id,review_until):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT)
        if not decision.allowed:
            return None
        if (not _valid_ref(source_ref) or not _valid_ref(evidence_ref)
                or not _valid_id(reviewer_id) or type(category) is not Category
                or type(metric) is not Metric or not _text(title,120)
                or not _text(hypothesis,1000)
                or type(target) is not int or not 1<=target<=10000
                or type(duration_seconds) is not int or not 60<=duration_seconds<=MAX_REVIEW
                or type(additional_cash_cents) is not int or additional_cash_cents!=0
                or type(review_until) is not int):
            raise ValueError("invalid zero-cash experiment")
        key=uuid4()
        mark=fingerprint(key,evidence)
        fields=("category","title","hypothesis","metric","target","duration_seconds",
                "additional_cash_cents","evidence_ref","evidence_sha256","evidence_size",
                "reviewer_id","review_until")
        values=(category.value,title,hypothesis,metric.value,target,duration_seconds,0,
                evidence_ref,mark.digest,mark.byte_count,reviewer_id,review_until)
        with locked(dsn) as (conn,_,now):
            old=conn.execute("SELECT * FROM business_opportunity WHERE source_ref=%s",
                             (source_ref,)).fetchone()
            if old:
                if tuple(old[k] for k in fields)!=values:
                    raise ValueError("conflicting opportunity")
                return JournalReceipt(old["id"],True)
            if not now<review_until<=now+MAX_REVIEW:
                raise ValueError("invalid review deadline")
            count=conn.execute("SELECT count(*) AS n FROM ("+LATEST+""") AS x
                WHERE action='started' OR
                ((action IS NULL OR action='approved') AND review_until>%s)""",(now,)).fetchone()["n"]
            if count>=MAX_OPEN:
                return None
            conn.execute("""INSERT INTO business_opportunity
                (id,source_ref,category,title,hypothesis,metric,target,duration_seconds,
                 additional_cash_cents,evidence_ref,evidence_sha256,evidence_size,
                 reviewer_id,review_until,created_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (key,source_ref,*values,now,decision.policy_version))
            return JournalReceipt(key)
    except Exception as exc:
        logger.error("Business proposal refused (%s)",type(exc).__name__)
        raise


def status(dsn,opportunity_id):
    try:
        if not _valid_id(opportunity_id):
            raise ValueError("invalid opportunity")
        with locked(dsn) as (conn,_,now):
            row=conn.execute(LATEST+" WHERE o.id=%s",(opportunity_id,)).fetchone()
            if row is None:
                return None
            state=row["action"] or "proposed"
            if state in ("approved","proposed") and row["review_until"]<=now:
                state="expired"
            if state=="started" and row["deadline"]<=now:
                state="overdue"
            return {"status":state,"metric":row["metric"],"target":row["target"],
                    "measured_count":row["measured_count"],
                    "target_met":None if row["measured_count"] is None else row["measured_count"]>=row["target"],
                    "additional_cash_cents":0,"authorized_cents":0}
    except Exception as exc:
        logger.error("Business experiment status unavailable (%s)",type(exc).__name__)
        raise
