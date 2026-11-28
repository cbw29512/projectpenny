"""Private canonical brand approval; no release, rendering or publication."""
import logging
import re
from hashlib import sha256

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id, _valid_ref
from penny.scheduler.storage_db import locked

logger = logging.getLogger(__name__)
MAX_ARTWORK_BYTES = 2097152
MAX_VERSIONS = 256


def _version(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", value) is not None


def _artwork_digest(artwork):
    # Hash exact bytes supplied by a trusted local operator; never fetch a URL.
    if type(artwork) is not bytes or not 1 <= len(artwork) <= MAX_ARTWORK_BYTES:
        raise ValueError("invalid artwork bytes")
    return sha256(artwork).hexdigest()


def approve(dsn, version, *, artwork, expected_sha256, reviewer_id,
            rights_ref, evidence, confirmed):
    """The authenticated Maker adapter must independently review artwork and rights."""
    try:
        decision = authorize(Actor.ADMIN, Capability.REVIEW_PRODUCT_CATALOG)
        if not decision.allowed:
            return False
        if (confirmed is not True or not _version(version)
                or not _valid_id(reviewer_id) or not _valid_ref(rights_ref)):
            raise ValueError("invalid brand approval")
        digest = _artwork_digest(artwork)
        if digest != expected_sha256:
            return False
        mark = fingerprint(reviewer_id, evidence)
        fields = ("artwork_sha256", "artwork_size", "reviewer_id",
                  "rights_ref", "evidence_sha256", "evidence_size")
        values = (digest, len(artwork), reviewer_id, rights_ref,
                  mark.digest, mark.byte_count)
        with locked(dsn) as (conn, _, now):
            prior = conn.execute(
                "SELECT * FROM product_brand_asset WHERE version=%s",
                (version,)).fetchone()
            if prior:
                if tuple(prior[k] for k in fields) != values:
                    raise ValueError("conflicting brand version")
                # Replay never reactivates a revoked asset.
                return False
            # Use the existing transaction lock: no two active canonical versions.
            if conn.execute("""SELECT 1 FROM product_brand_asset a
                LEFT JOIN product_brand_revocation r ON r.version=a.version
                WHERE r.version IS NULL LIMIT 1""").fetchone():
                return False
            count = conn.execute("SELECT count(*) AS n FROM product_brand_asset").fetchone()
            if count["n"] >= MAX_VERSIONS:
                return False
            conn.execute("""INSERT INTO product_brand_asset
                (version,artwork_sha256,artwork_size,reviewer_id,rights_ref,
                 evidence_sha256,evidence_size,approved_name,approved_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'Penny',%s,%s)""",
                (version, *values, now, decision.policy_version))
            return True
    except Exception as exc:
        logger.error("Brand approval refused (%s)", type(exc).__name__)
        raise


def revoke(dsn, version, *, reviewer_id, evidence_ref, evidence, confirmed):
    """Append a permanent withdrawal; use a new reviewed version to replace it."""
    try:
        decision = authorize(Actor.ADMIN, Capability.REVIEW_PRODUCT_CATALOG)
        if not decision.allowed:
            return False
        if (confirmed is not True or not _version(version)
                or not _valid_id(reviewer_id) or not _valid_ref(evidence_ref)):
            raise ValueError("invalid brand revocation")
        mark = fingerprint(reviewer_id, evidence)
        with locked(dsn) as (conn, _, now):
            if not conn.execute("SELECT 1 FROM product_brand_asset WHERE version=%s",
                                (version,)).fetchone():
                return False
            return conn.execute("""INSERT INTO product_brand_revocation
                (version,reviewer_id,evidence_ref,evidence_sha256,evidence_size,
                 revoked_at,policy_version) VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING RETURNING version""",
                (version, reviewer_id, evidence_ref, mark.digest, mark.byte_count,
                 now, decision.policy_version)).fetchone() is not None
    except Exception as exc:
        logger.error("Brand revocation refused (%s)", type(exc).__name__)
        raise


def matches_locked(conn, version, artwork):
    """Verify actual bytes in the caller's transaction, not a model-supplied hash.

    Future release adapters must also bind and review exact rendered bytes,
    check source eligibility, and enforce separate publication authorization.
    """
    try:
        if not _version(version):
            return False
        digest = _artwork_digest(artwork)
        row = conn.execute("""SELECT a.artwork_sha256,a.artwork_size,a.approved_name
            FROM product_brand_asset a LEFT JOIN product_brand_revocation r
            ON r.version=a.version WHERE a.version=%s AND r.version IS NULL""",
            (version,)).fetchone()
        return bool(row and row["approved_name"] == "Penny"
                    and row["artwork_sha256"] == digest
                    and row["artwork_size"] == len(artwork))
    except (TypeError, ValueError):
        logger.warning("Brand verification rejected invalid input")
        return False
    except Exception as exc:
        logger.error("Brand verification failed (%s)", type(exc).__name__)
        raise
