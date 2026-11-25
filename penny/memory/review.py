"""Internal administrator review boundary; never expose to model or public API."""
import logging
import re
from uuid import UUID

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .evidence import fingerprint
from .review_state import MAX_RETENTION_SECONDS

logger = logging.getLogger(__name__)


def _valid_id(value):
    return type(value) is UUID and value.int != 0


def _valid_ref(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", value) is not None


def approve(dsn, source_id, *, reviewer_id, review_ref, evidence, expected_content, retention_seconds):
    """Trusted admin adapter must authenticate reviewer and independently assess evidence.

    The fingerprint proves byte integrity, not truth. The expected content binds
    explicit human review to the candidate being approved; never infer approval.
    """
    try:
        decision = authorize(Actor.ADMIN, Capability.APPROVE_BUSINESS_MEMORY)
        if not decision.allowed:
            return False
        if not _valid_id(source_id) or not _valid_id(reviewer_id) or not _valid_ref(review_ref):
            raise ValueError("invalid review identity")
        if type(expected_content) is not str or not 1 <= len(expected_content) <= 1000:
            raise ValueError("invalid reviewed content")
        if type(retention_seconds) is not int or not 1 <= retention_seconds <= MAX_RETENTION_SECONDS:
            raise ValueError("invalid retention")
        mark = fingerprint(source_id, evidence)
        with locked(dsn) as (conn, _, now):
            row = conn.execute(
                """SELECT c.kind,c.content FROM memory_candidate c
                   JOIN work_task t ON t.id=c.source_task_id
                   JOIN task_outcome o ON o.task_id=t.id
                   WHERE c.source_task_id=%s AND t.member_id IS NULL
                   AND o.status='succeeded' AND c.validation_state='quarantined'""",
                (source_id,),
            ).fetchone()
            if not row or row["content"] != expected_content:
                return False
            inserted = conn.execute(
                """INSERT INTO business_memory
                   (source_task_id,kind,content,evidence_sha256,evidence_size,review_ref,
                    reviewed_by,approved_at,expires_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (source_task_id) DO NOTHING RETURNING source_task_id""",
                (source_id,row["kind"],row["content"],mark.digest,mark.byte_count,review_ref,
                 reviewer_id,now,now+retention_seconds),
            ).fetchone()
            if not inserted:
                return False
            conn.execute(
                """INSERT INTO business_memory_event VALUES (%s,'approved',%s,%s,%s,%s)""",
                (source_id,reviewer_id,review_ref,now,decision.policy_version),
            )
            return True
    except Exception as exc:
        logger.error("Business memory approval failed (%s)", type(exc).__name__)
        raise


def revoke(dsn, source_id, *, reviewer_id, review_ref):
    """Revoke once; no deletion or silent restoration of previous approval."""
    try:
        decision = authorize(Actor.ADMIN, Capability.REVOKE_BUSINESS_MEMORY)
        if not decision.allowed:
            return False
        if not _valid_id(source_id) or not _valid_id(reviewer_id) or not _valid_ref(review_ref):
            raise ValueError("invalid revocation identity")
        with locked(dsn) as (conn, _, now):
            row = conn.execute(
                """UPDATE business_memory SET revoked_at=GREATEST(%s,approved_at)
                   WHERE source_task_id=%s AND revoked_at IS NULL RETURNING source_task_id""",
                (now,source_id),
            ).fetchone()
            if not row:
                return False
            conn.execute(
                """INSERT INTO business_memory_event VALUES (%s,'revoked',%s,%s,%s,%s)""",
                (source_id,reviewer_id,review_ref,now,decision.policy_version),
            )
            return True
    except Exception as exc:
        logger.error("Business memory revocation failed (%s)", type(exc).__name__)
        raise
