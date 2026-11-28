"""Preview, exact human review and cached read. No deployment or publication."""
import logging
from uuid import uuid4

from psycopg.types.json import Jsonb
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked
from penny.vault.reconciliation import MAX_AGE as FINANCE_MAX_AGE
from penny.vault.state import JournalReceipt
from .derive import derive
from .state import MAX_AGE,digest,validate

logger=logging.getLogger(__name__)


def _flags(finance,business):
    if type(finance) is not bool or type(business) is not bool:
        raise ValueError("explicit disclosure choices required")


def preview(dsn,*,finance=False,business=False):
    try:
        _flags(finance,business)
        if not authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            data=derive(conn,now,finance=finance,business=business)
            return {"payload":data,"digest":digest(data)}
    except Exception as exc:
        logger.error("Progress preview unavailable (%s)",type(exc).__name__)
        raise


def record_snapshot(dsn,*,source_ref,expected_digest,finance,business,
                    reviewer_id,evidence_ref,evidence,confirmed):
    """Review exact aggregate content and coverage. No live publication."""
    try:
        _flags(finance,business)
        decision=authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT)
        if not decision.allowed:
            return None
        if (confirmed is not True or not _valid_id(reviewer_id) or not _valid_ref(source_ref)
                or not _valid_ref(evidence_ref) or type(expected_digest) is not str
                or len(expected_digest)!=64):
            raise ValueError("invalid snapshot review")
        key=uuid4()
        mark=fingerprint(key,evidence)
        with locked(dsn) as (conn,_,now):
            old=conn.execute("SELECT * FROM progress_snapshot WHERE source_ref=%s",
                             (source_ref,)).fetchone()
            if old:
                if (old["payload_sha256"],old["reviewer_id"],old["evidence_ref"],
                    old["evidence_sha256"],old["evidence_size"])!=(
                    expected_digest,reviewer_id,evidence_ref,mark.digest,mark.byte_count):
                    raise ValueError("conflicting snapshot review")
                return JournalReceipt(old["id"],True)
            data=derive(conn,now,finance=finance,business=business)
            if digest(data)!=expected_digest:
                return None
            expires=now+MAX_AGE
            if data["finance"] is not None:
                expires=min(expires,data["finance"]["statement_at"]+FINANCE_MAX_AGE)
            if expires<=now:
                return None
            conn.execute("""INSERT INTO progress_snapshot
                (id,source_ref,payload,payload_sha256,generated_at,expires_at,reviewer_id,
                 evidence_ref,evidence_sha256,evidence_size,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (key,source_ref,Jsonb(data),expected_digest,now,expires,reviewer_id,
                 evidence_ref,mark.digest,mark.byte_count,decision.policy_version))
            return JournalReceipt(key)
    except Exception as exc:
        logger.error("Progress snapshot review refused (%s)",type(exc).__name__)
        raise


def cached(dsn):
    """Local candidate read; no source queries or inference, never public transport."""
    try:
        if not authorize(Actor.ADMIN,Capability.REVIEW_PROGRESS_SNAPSHOT).allowed:
            return {"status":"unavailable","payload":None}
        with locked(dsn) as (conn,_,now):
            row=conn.execute("""SELECT version,payload,payload_sha256,generated_at,expires_at
                FROM progress_snapshot ORDER BY version DESC LIMIT 1""").fetchone()
            if not row:
                return {"status":"unavailable","payload":None}
            payload=validate(row["payload"])
            if digest(payload)!=row["payload_sha256"]:
                raise ValueError("snapshot integrity mismatch")
            fresh=row["generated_at"]<=now<row["expires_at"]
            return {"status":"reviewed" if fresh else "stale","version":row["version"],
                    "generated_at":row["generated_at"],"expires_at":row["expires_at"],
                    "payload":payload if fresh else None}
    except Exception as exc:
        logger.error("Progress cached read unavailable (%s)",type(exc).__name__)
        return {"status":"unavailable","payload":None}
