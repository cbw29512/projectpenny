"""Trusted local beta authorization and permanent revocation."""
import logging
import re

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked
from .beta_proof import proof_locked
from .brand import _version

logger=logging.getLogger(__name__)
MAX_RECORDS=4096
MAX_PER_PREVIEW=20
MAX_AGE=604800


def grant_beta(dsn,grant_id,*,preview_id,member_id,quality_review_id,brand_version,
               edition_sha256,variant_sha256,artwork,reviewer_id,evidence_ref,evidence,
               expires_at,confirmed):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_PRODUCT_CATALOG)
        if not decision.allowed:
            return False
        if (confirmed is not True or not all(_valid_id(x) for x in
                (grant_id,preview_id,member_id,quality_review_id,reviewer_id))
                or not _version(brand_version) or not _valid_ref(evidence_ref)
                or type(expires_at) is not int
                or any(type(x) is not str or not re.fullmatch(r"[a-f0-9]{64}",x)
                       for x in (edition_sha256,variant_sha256))):
            raise ValueError("invalid beta grant")
        mark=fingerprint(grant_id,evidence)
        with locked(dsn) as (conn,control,now):
            # Refuse new disclosure during stop, and never reissue a used ID
            # or extend an existing tester's grant by replay.
            if control["paused"] or not now<expires_at<=now+MAX_AGE:
                return False
            preview=conn.execute("SELECT expires_at FROM workshop_preview WHERE id=%s",
                                 (preview_id,)).fetchone()
            if not preview or expires_at>preview["expires_at"]:
                return False
            if conn.execute("""SELECT 1 FROM workshop_beta_grant WHERE id=%s
                OR (preview_id=%s AND member_id=%s)""",(grant_id,preview_id,member_id)).fetchone():
                return False
            if not conn.execute("""SELECT 1 FROM member_session WHERE member_id=%s
                AND revoked_at IS NULL AND expires_at>%s LIMIT 1""",(member_id,now)).fetchone():
                return False
            counts=conn.execute("""SELECT count(*) AS total,
                count(*) FILTER(WHERE preview_id=%s) AS own FROM workshop_beta_grant""",
                (preview_id,)).fetchone()
            if counts["total"]>=MAX_RECORDS or counts["own"]>=MAX_PER_PREVIEW:
                return False
            proof=proof_locked(conn,preview_id,grant_id,now,quality_review_id=quality_review_id,
                               brand_version=brand_version,artwork=artwork)
            if not proof or (proof.edition_sha256,proof.variant_sha256)!=(edition_sha256,variant_sha256):
                return False
            conn.execute("""INSERT INTO workshop_beta_grant
                (id,preview_id,member_id,quality_review_id,brand_version,edition_sha256,
                 variant_sha256,reviewer_id,evidence_ref,evidence_sha256,evidence_size,
                 granted_at,expires_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (grant_id,preview_id,member_id,quality_review_id,brand_version,edition_sha256,
                 variant_sha256,reviewer_id,evidence_ref,mark.digest,mark.byte_count,
                 now,expires_at,decision.policy_version))
            return True
    except Exception as exc:
        logger.error("Beta grant refused (%s)",type(exc).__name__)
        raise


def revoke_beta(dsn,grant_id,*,reviewer_id,evidence_ref,evidence,confirmed):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_PRODUCT_CATALOG)
        if not decision.allowed:
            return False
        if (confirmed is not True or not _valid_id(grant_id)
                or not _valid_id(reviewer_id) or not _valid_ref(evidence_ref)):
            raise ValueError("invalid beta revocation")
        mark=fingerprint(grant_id,evidence)
        with locked(dsn) as (conn,_,now):
            if not conn.execute("SELECT 1 FROM workshop_beta_grant WHERE id=%s",(grant_id,)).fetchone():
                return False
            return conn.execute("""INSERT INTO workshop_beta_revocation
                VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING grant_id""",
                (grant_id,reviewer_id,evidence_ref,mark.digest,mark.byte_count,now,
                 decision.policy_version)).fetchone() is not None
    except Exception as exc:
        logger.error("Beta revocation refused (%s)",type(exc).__name__)
        raise
