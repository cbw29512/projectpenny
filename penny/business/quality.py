"""Private evidence-reviewed export, not a commercial release."""
import logging
import re
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked
from penny.vault.state import JournalReceipt
from .quality_state import CRITERIA,PrivateExport
from .workshop_intake import read_locked

logger=logging.getLogger(__name__)


def _latest(conn,task_id):
    return conn.execute("""SELECT * FROM workshop_quality_review
        WHERE task_id=%s ORDER BY sequence DESC LIMIT 1""",(task_id,)).fetchone()


def _verdict(row):
    if row is None:
        return "unreviewed"
    if row["revoked"]:
        return "revoked"
    return "passed" if all(row[k] for k in CRITERIA) else "failed"


def review(dsn,task_id,*,source_ref,expected_content_sha256,checks,revoked,
           reviewer_id,evidence_ref,evidence,confirmed):
    """Trusted administrator independently reviews exact bytes; no model approval."""
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT)
        if not decision.allowed:
            return None
        if (not _valid_id(task_id) or not _valid_id(reviewer_id)
                or not _valid_ref(source_ref) or not _valid_ref(evidence_ref)
                or confirmed is not True or type(revoked) is not bool
                or type(expected_content_sha256) is not str
                or not re.fullmatch(r"[a-f0-9]{64}",expected_content_sha256)
                or type(checks) is not dict or set(checks)!=set(CRITERIA)
                or any(type(checks[k]) is not bool for k in CRITERIA)
                or (revoked and any(checks.values()))):
            raise ValueError("invalid product review")
        key=uuid4()
        mark=fingerprint(key,evidence)
        fields=("task_id","content_sha256",*CRITERIA,"revoked","reviewer_id",
                "evidence_ref","evidence_sha256","evidence_size")
        values=(task_id,expected_content_sha256,*(checks[k] for k in CRITERIA),
                revoked,reviewer_id,evidence_ref,mark.digest,mark.byte_count)
        with locked(dsn) as (conn,_,now):
            old=conn.execute("SELECT * FROM workshop_quality_review WHERE source_ref=%s",
                             (source_ref,)).fetchone()
            if old:
                if tuple(old[k] for k in fields)!=values:
                    raise ValueError("conflicting product review")
                return JournalReceipt(old["id"],True)
            latest=_latest(conn,task_id)
            if revoked:
                # Revoke even if artifact bytes are now corrupt. Terminal for this version.
                if latest is None or latest["revoked"] or latest["content_sha256"]!=expected_content_sha256:
                    return None
            else:
                if latest and latest["revoked"]:
                    return None
                artifact=read_locked(conn,task_id,now)
                if (not artifact or artifact["status"]!="private_prototype"
                        or artifact["artifact"]["content_sha256"]!=expected_content_sha256):
                    return None
            conn.execute("""INSERT INTO workshop_quality_review
                (id,source_ref,task_id,content_sha256,usefulness,accuracy,originality,
                 privacy,completeness,revoked,reviewer_id,evidence_ref,evidence_sha256,
                 evidence_size,reviewed_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (key,source_ref,*values,now,decision.policy_version))
            return JournalReceipt(key)
    except Exception as exc:
        logger.error("Workshop quality review refused (%s)",type(exc).__name__)
        raise


def quality_status(dsn,task_id):
    try:
        if not _valid_id(task_id):
            raise ValueError("invalid artifact ID")
        if not authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            artifact=read_locked(conn,task_id,now)
            if artifact is None:
                return None
            row=_latest(conn,task_id)
            state=_verdict(row)
            if artifact["status"]!="private_prototype" or (row and
                    artifact["artifact"]["content_sha256"]!=row["content_sha256"]):
                state="unavailable"
            return {"status":state,"private_export_ready":state=="passed",
                    "commercial_release_authorized":False}
    except Exception as exc:
        logger.error("Workshop quality status unavailable (%s)",type(exc).__name__)
        raise


def export_private(dsn,task_id,*,expected_review_id,expected_content_sha256):
    """Return inert bytes to trusted caller only, never write or publish a file."""
    try:
        if not _valid_id(task_id) or not _valid_id(expected_review_id):
            raise ValueError("invalid export identity")
        if not authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            row=_latest(conn,task_id)
            if (_verdict(row)!="passed" or row["id"]!=expected_review_id
                    or row["content_sha256"]!=expected_content_sha256):
                return None
            artifact=read_locked(conn,task_id,now)
            if not artifact or artifact["status"]!="private_prototype":
                return None
            data=artifact["artifact"]
            if data["content_sha256"]!=expected_content_sha256:
                return None
            return PrivateExport("penny-checklist-"+str(task_id)+".txt",
                                 "text/plain; charset=utf-8",data["content_sha256"],
                                 data["content"].encode("utf-8"))
    except Exception as exc:
        logger.error("Workshop private export refused (%s)",type(exc).__name__)
        raise
