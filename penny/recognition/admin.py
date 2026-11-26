"""Trusted administrator evidence review; no model or member approval authority."""
import logging
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id, _valid_ref
from penny.scheduler.storage_db import locked
from .state import Outcome, CONSENT_VERSION

logger = logging.getLogger(__name__)


def record_outcome(dsn, *, outcome_ref, verdict, evidence, reviewer_id):
    """Only authenticated internal reviewer may attest an independently measured outcome."""
    try:
        decision = authorize(Actor.ADMIN,Capability.VERIFY_CONTRIBUTION)
        if not decision.allowed:
            return None
        if not _valid_ref(outcome_ref) or not _valid_id(reviewer_id) or type(verdict) is not Outcome:
            raise ValueError("invalid outcome review")
        outcome_id = uuid4()
        mark = fingerprint(outcome_id,evidence)
        with locked(dsn) as (conn,_,now):
            old = conn.execute("SELECT id,verdict,evidence_sha256 FROM contribution_outcome WHERE outcome_ref=%s",
                               (outcome_ref,)).fetchone()
            if old:
                if old["verdict"] != verdict.value or old["evidence_sha256"] != mark.digest:
                    raise ValueError("conflicting outcome evidence")
                return old["id"]
            conn.execute("INSERT INTO contribution_outcome VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                         (outcome_id,outcome_ref,verdict.value,mark.digest,mark.byte_count,
                          reviewer_id,now,decision.policy_version))
            return outcome_id
    except Exception as exc:
        logger.error("Contribution outcome review failed (%s)",type(exc).__name__)
        raise


def verify_request(dsn, request_id, *, reviewer_id, evidence_ref, evidence):
    """Evidence must substantiate this exact member/outcome/role, not merely the outcome."""
    try:
        decision = authorize(Actor.ADMIN,Capability.VERIFY_CONTRIBUTION)
        if not decision.allowed:
            return False
        if not _valid_id(request_id) or not _valid_id(reviewer_id) or not _valid_ref(evidence_ref):
            raise ValueError("invalid attribution review")
        mark = fingerprint(request_id,evidence)
        with locked(dsn) as (conn,_,now):
            row = conn.execute("SELECT id FROM contribution_request WHERE id=%s AND consent_version=%s",
                               (request_id,CONSENT_VERSION)).fetchone()
            if not row:
                return False
            return conn.execute(
                """INSERT INTO contribution_recognition VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (request_id) DO NOTHING RETURNING request_id""",
                (request_id,evidence_ref,mark.digest,mark.byte_count,reviewer_id,now,decision.policy_version),
            ).fetchone() is not None
    except Exception as exc:
        logger.error("Contribution attribution review failed (%s)",type(exc).__name__)
        raise
