"""Explicit achievement review, historical retention, and current eligibility."""
import logging
import re
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked
from penny.vault.state import JournalReceipt
from .achievement_state import Achievement,SCHEMA,MAX_AGE
from .achievement_source import source_locked

logger=logging.getLogger(__name__)


def _latest(conn,code):
    return conn.execute("""SELECT * FROM achievement_review WHERE code=%s
        ORDER BY sequence DESC LIMIT 1""",(code.value,)).fetchone()


def preview(dsn,code):
    try:
        if type(code) is not Achievement:
            raise ValueError("invalid achievement")
        if not authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            source=source_locked(conn,now,code)
            return {"eligible":source is not None,
                    "source_digest":source[0] if source else None}
    except Exception as exc:
        logger.error("Achievement preview unavailable (%s)",type(exc).__name__)
        raise


def review(dsn,code,*,source_ref,expected_digest,approved,reviewer_id,
           evidence_ref,evidence,confirmed):
    """Administrator confirms disclosure of exact source or withdraws prior review."""
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT)
        if not decision.allowed:
            return None
        if (type(code) is not Achievement or type(approved) is not bool
                or confirmed is not True or not _valid_id(reviewer_id)
                or not _valid_ref(source_ref) or not _valid_ref(evidence_ref)
                or type(expected_digest) is not str
                or not re.fullmatch(r"[a-f0-9]{64}",expected_digest)):
            raise ValueError("invalid achievement review")
        key=uuid4()
        mark=fingerprint(key,evidence)
        fields=("code","source_sha256","approved","reviewer_id","evidence_ref",
                "evidence_sha256","evidence_size")
        values=(code.value,expected_digest,approved,reviewer_id,evidence_ref,
                mark.digest,mark.byte_count)
        with locked(dsn) as (conn,_,now):
            old=conn.execute("SELECT * FROM achievement_review WHERE source_ref=%s",
                             (source_ref,)).fetchone()
            if old:
                if tuple(old[k] for k in fields)!=values:
                    raise ValueError("conflicting achievement review")
                return JournalReceipt(old["id"],True)
            if approved:
                source=source_locked(conn,now,code)
                if source is None or source[0]!=expected_digest:
                    return None
            else:
                old=_latest(conn,code)
                if not old or not old["approved"] or old["source_sha256"]!=expected_digest:
                    return None
            conn.execute("""INSERT INTO achievement_review
                (id,source_ref,code,source_sha256,approved,reviewer_id,evidence_ref,
                 evidence_sha256,evidence_size,reviewed_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (key,source_ref,*values,now,decision.policy_version))
            return JournalReceipt(key)
    except Exception as exc:
        logger.error("Achievement review refused (%s)",type(exc).__name__)
        raise


def browser_candidate(dsn):
    """Local candidate only: never auto-unlock or expose internal source IDs."""
    unavailable={"schema":SCHEMA,"status":"unavailable","achievements":[]}
    try:
        if not authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT).allowed:
            return unavailable
        with locked(dsn) as (conn,_,now):
            results=[]
            expires=now+MAX_AGE
            for code in Achievement:
                row=_latest(conn,code)
                state="unverified"
                day=None
                if row:
                    if not row["approved"]:
                        state="withdrawn"
                    else:
                        source=source_locked(conn,now,code)
                        if source and source[0]==row["source_sha256"] and row["reviewed_at"]<=now:
                            state="verified"
                            day=row["reviewed_at"]//86400*86400
                            expires=min(expires,source[1])
                        else:
                            state="needs_review"
                results.append({"code":code.value,"status":state,"review_day":day})
            return {"schema":SCHEMA,"status":"reviewed","generated_at":now,
                    "expires_at":expires,"achievements":results}
    except Exception as exc:
        logger.error("Achievement candidate unavailable (%s)",type(exc).__name__)
        return unavailable
