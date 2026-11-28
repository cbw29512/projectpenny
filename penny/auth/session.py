"""Opaque member sessions for a trusted, separately verified identity adapter."""
import hashlib
import logging
import re
import secrets
from uuid import UUID, uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .state import IssuedSession, SESSION_SECONDS, MAX_ACTIVE_SESSIONS

logger = logging.getLogger(__name__)


def _digest(token):
    # A 32-byte random URL-safe credential has 43 characters without padding.
    if type(token) is not str or re.fullmatch(r"[A-Za-z0-9_-]{43}",token) is None:
        raise PermissionError("invalid session")
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def issue_session(dsn, verified_member_id):
    """Trusted administrator/identity adapter only, AFTER identity verification.

    No password or external identity provider is implemented by this function.
    Never let an HTTP client supply verified_member_id.
    """
    try:
        if type(verified_member_id) is not UUID or verified_member_id.int == 0:
            raise ValueError("invalid verified identity")
        if not authorize(Actor.ADMIN,Capability.ISSUE_MEMBER_SESSION).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            count = conn.execute(
                """SELECT count(*) AS n FROM member_session
                   WHERE member_id=%s AND revoked_at IS NULL AND expires_at>%s""",
                (verified_member_id,now),
            ).fetchone()["n"]
            if count >= MAX_ACTIVE_SESSIONS:
                return None
            token = secrets.token_urlsafe(32)
            session = IssuedSession(uuid4(),token,now+SESSION_SECONDS)
            conn.execute(
                "INSERT INTO member_session (id,member_id,token_sha256,issued_at,expires_at) VALUES (%s,%s,%s,%s,%s)",
                (session.id,verified_member_id,_digest(token),now,session.expires_at),
            )
            return session
    except Exception as exc:
        logger.error("Session issuance failed (%s)",type(exc).__name__)
        raise


def resolve_member(conn, now, token):
    """Called inside the same locked transaction as the protected operation."""
    try:
        row = conn.execute(
            """SELECT member_id FROM member_session WHERE token_sha256=%s
               AND revoked_at IS NULL AND expires_at>%s""",
            (_digest(token),now),
        ).fetchone()
        if not row:
            raise PermissionError("invalid session")
        return row["member_id"]
    except Exception as exc:
        logger.info("Session resolution failed (%s)",type(exc).__name__)
        raise


def revoke_session(dsn, token):
    """Holder may terminate its own session even during identity failure."""
    try:
        digest = _digest(token)
        with locked(dsn) as (conn,_,now):
            return conn.execute(
                """UPDATE member_session SET revoked_at=GREATEST(%s,issued_at)
                   WHERE token_sha256=%s AND revoked_at IS NULL RETURNING id""",
                (now,digest),
            ).fetchone() is not None
    except Exception as exc:
        logger.info("Session revocation failed (%s)",type(exc).__name__)
        raise
