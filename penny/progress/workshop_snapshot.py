"""Local explicitly reviewed Workshop disclosure; no public transport."""
import logging
import re
from uuid import uuid4
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked
from penny.vault.state import JournalReceipt
from .workshop_source import SCHEMA,PRODUCT,STAGES,MAX_AGE,source_locked,unavailable

logger=logging.getLogger(__name__)


def _validate(product_id,stage,preview_id):
    if (not _valid_id(product_id) or type(stage) is not str or stage not in STAGES
            or (preview_id is not None and not _valid_id(preview_id))
            or (stage=="preview_reviewed" and preview_id is None)
            or (stage in ("prototype_reviewed","revision_reviewed") and preview_id is not None)):
        raise ValueError("invalid Workshop disclosure source")


def preview(dsn,product_id,*,stage,preview_id=None):
    try:
        _validate(product_id,stage,preview_id)
        if not authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            source=source_locked(conn,product_id,stage,preview_id,now)
            return None if source is None else {"product":PRODUCT,"stage":stage,"source_sha256":source[0]}
    except Exception as exc:
        logger.error("Workshop progress preview refused (%s)",type(exc).__name__)
        raise


def record(dsn,product_id,*,stage,preview_id=None,source_ref,expected_digest,
           reviewer_id,evidence_ref,evidence,confirmed):
    try:
        _validate(product_id,stage,preview_id)
        decision=authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT)
        if not decision.allowed:
            return None
        if (confirmed is not True or not _valid_id(reviewer_id) or not _valid_ref(source_ref)
                or not _valid_ref(evidence_ref) or type(expected_digest) is not str
                or not re.fullmatch(r"[a-f0-9]{64}",expected_digest)):
            raise ValueError("invalid Workshop progress review")
        key=uuid4()
        mark=fingerprint(key,evidence)
        fields=("product_id","preview_id","stage","source_sha256","reviewer_id",
                "evidence_ref","evidence_sha256","evidence_size")
        values=(product_id,preview_id,stage,expected_digest,reviewer_id,
                evidence_ref,mark.digest,mark.byte_count)
        with locked(dsn) as (conn,_,now):
            old=conn.execute("SELECT * FROM workshop_progress_snapshot WHERE source_ref=%s",
                             (source_ref,)).fetchone()
            if old:
                if tuple(old[k] for k in fields)!=values:
                    raise ValueError("conflicting Workshop progress review")
                return JournalReceipt(old["id"],True)
            source=source_locked(conn,product_id,stage,preview_id,now)
            if source is None or source[0]!=expected_digest:
                return None
            expiry=min(now+MAX_AGE,source[1]) if source[1] is not None else now+MAX_AGE
            if expiry<=now:
                return None
            conn.execute("""INSERT INTO workshop_progress_snapshot
                (id,source_ref,product_id,preview_id,stage,source_sha256,reviewer_id,
                 evidence_ref,evidence_sha256,evidence_size,generated_at,expires_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (key,source_ref,*values,now,expiry,decision.policy_version))
            return JournalReceipt(key)
    except Exception as exc:
        logger.error("Workshop progress review refused (%s)",type(exc).__name__)
        raise


def browser_candidate(dsn):
    try:
        if not authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT).allowed:
            return unavailable()
        with locked(dsn) as (conn,_,now):
            return candidate_locked(conn,now)
    except Exception as exc:
        logger.error("Workshop browser candidate unavailable (%s)",type(exc).__name__)
        return unavailable()


def candidate_locked(conn,now):
    """Trusted caller holds scheduler lock; exact source recheck."""
    row=conn.execute("""SELECT * FROM workshop_progress_snapshot
        ORDER BY sequence DESC LIMIT 1""").fetchone()
    if not row or not row["generated_at"]<=now<row["expires_at"]:
        return unavailable()
    _validate(row["product_id"],row["stage"],row["preview_id"])
    source=source_locked(conn,row["product_id"],row["stage"],row["preview_id"],now)
    if not source or source[0]!=row["source_sha256"]:
        return unavailable()
    return {"schema":SCHEMA,"status":"reviewed","product":PRODUCT,"stage":row["stage"],
            "generated_at":row["generated_at"],"expires_at":row["expires_at"]}
