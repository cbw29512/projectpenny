"""Trusted authenticated member adapter only; UUID is not authentication."""
import logging
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.auth.member_scope import member_scope
from .member_state import CONSENT_VERSION, CONSENT_SECONDS, MemberConsent
from .review import _valid_id

logger = logging.getLogger(__name__)


def active_consent(conn, member_id, now):
    return conn.execute(
        """SELECT epoch,expires_at FROM member_memory_consent
           WHERE member_id=%s AND enabled AND policy_version=%s AND expires_at>%s""",
        (member_id,CONSENT_VERSION,now),
    ).fetchone()


def opt_in(dsn, member_id, *, accepted_version, _session_token=None):
    """Explicit member action, never inferred from chat or payment."""
    try:
        if (_session_token is None and not _valid_id(member_id)) or accepted_version != CONSENT_VERSION:
            raise ValueError("invalid consent request")
        if not authorize(Actor.MEMBER,Capability.MANAGE_OWN_MEMORY).allowed:
            return None
        with member_scope(dsn,member_id,_session_token) as (conn,_,now,member_id):
            active = active_consent(conn,member_id,now)
            if active:
                return MemberConsent(active["epoch"],active["expires_at"])
            # A new consent epoch never resurrects preferences from a prior epoch.
            conn.execute("DELETE FROM member_memory WHERE member_id=%s",(member_id,))
            epoch, expires = uuid4(),now+CONSENT_SECONDS
            conn.execute(
                """INSERT INTO member_memory_consent VALUES (%s,%s,true,%s,%s,%s)
                   ON CONFLICT (member_id) DO UPDATE SET epoch=EXCLUDED.epoch,
                   enabled=true,policy_version=EXCLUDED.policy_version,
                   granted_at=EXCLUDED.granted_at,expires_at=EXCLUDED.expires_at""",
                (member_id,epoch,CONSENT_VERSION,now,expires),
            )
            conn.execute("INSERT INTO member_memory_consent_event VALUES (%s,%s,%s,'granted',%s,%s)",
                         (uuid4(),member_id,epoch,CONSENT_VERSION,now))
            return MemberConsent(epoch,expires)
    except Exception as exc:
        logger.error("Member memory consent failed (%s)",type(exc).__name__)
        raise


def withdraw(dsn, member_id, *, _session_token=None):
    """Disable and remove live preference rows atomically, even after expiry."""
    try:
        if (_session_token is None and not _valid_id(member_id)):
            raise ValueError("invalid member")
        if not authorize(Actor.MEMBER,Capability.WITHDRAW_MEMORY_CONSENT).allowed:
            return False
        with member_scope(dsn,member_id,_session_token) as (conn,_,now,member_id):
            row = conn.execute(
                "SELECT epoch,policy_version,enabled FROM member_memory_consent WHERE member_id=%s",
                (member_id,),
            ).fetchone()
            conn.execute("DELETE FROM member_memory WHERE member_id=%s",(member_id,))
            if not row or not row["enabled"]:
                return False
            conn.execute("UPDATE member_memory_consent SET enabled=false WHERE member_id=%s",(member_id,))
            conn.execute("INSERT INTO member_memory_consent_event VALUES (%s,%s,%s,'withdrawn',%s,%s)",
                         (uuid4(),member_id,row["epoch"],row["policy_version"],now))
            return True
    except Exception as exc:
        logger.error("Member memory withdrawal failed (%s)",type(exc).__name__)
        raise
