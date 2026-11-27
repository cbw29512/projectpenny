"""Local trusted delivery adapter; no public endpoint, cache or file URL."""
import logging
from penny.auth.session import resolve_member
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.review import _valid_id
from penny.scheduler.storage_db import locked
from .beta_proof import proof_locked

logger=logging.getLogger(__name__)


def read_beta(dsn,token,grant_id,*,artwork):
    """Artwork supplied by trusted local adapter, never by a member upload."""
    try:
        if not _valid_id(grant_id):
            raise ValueError("invalid beta grant")
        if not authorize(Actor.MEMBER,Capability.READ_BETA_EDITION).allowed:
            return None
        with locked(dsn) as (conn,control,now):
            owner=resolve_member(conn,now,token)
            if control["paused"]:
                return None
            row=conn.execute("""SELECT g.* FROM workshop_beta_grant g
                LEFT JOIN workshop_beta_revocation r ON r.grant_id=g.id
                WHERE g.id=%s AND g.member_id=%s AND g.expires_at>%s
                  AND r.grant_id IS NULL""",(grant_id,owner,now)).fetchone()
            if row is None:
                return None
            proof=proof_locked(conn,row["preview_id"],grant_id,now,
                quality_review_id=row["quality_review_id"],brand_version=row["brand_version"],
                artwork=artwork)
            if not proof or (proof.edition_sha256,proof.variant_sha256)!=(
                    row["edition_sha256"],row["variant_sha256"]):
                return None
            return proof
    except Exception as exc:
        logger.error("Beta access refused (%s)",type(exc).__name__)
        raise
