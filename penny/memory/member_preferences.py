"""Explicit owner-managed preferences; no model extraction or recall integration."""
import logging
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .member_consent import active_consent
from .member_state import MAX_MEMBER_MEMORIES, MAX_PREFERENCE_CHARS, MemberPreference
from .review import _valid_id

logger = logging.getLogger(__name__)


def save_preference(dsn, member_id, epoch, preference):
    try:
        if not _valid_id(member_id) or not _valid_id(epoch):
            raise ValueError("invalid owner or consent epoch")
        if type(preference) is not str or not 1 <= len(preference.strip()) <= MAX_PREFERENCE_CHARS or "\x00" in preference:
            raise ValueError("invalid preference")
        preference = preference.strip()
        preference.encode("utf-8")
        if not authorize(Actor.MEMBER,Capability.MANAGE_OWN_MEMORY).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            consent = active_consent(conn,member_id,now)
            if not consent or consent["epoch"] != epoch:
                return None
            rows = conn.execute("SELECT id,preference FROM member_memory WHERE member_id=%s AND epoch=%s",
                                (member_id,epoch)).fetchall()
            for row in rows:
                if row["preference"] == preference:
                    return MemberPreference(row["id"],preference)
            if len(rows) >= MAX_MEMBER_MEMORIES:
                return None
            item = MemberPreference(uuid4(),preference)
            conn.execute("INSERT INTO member_memory VALUES (%s,%s,%s,%s,%s)",
                         (member_id,epoch,item.id,item.preference,now))
            return item
    except Exception as exc:
        logger.error("Member preference save failed (%s)",type(exc).__name__)
        raise


def list_preferences(dsn, member_id):
    try:
        if not _valid_id(member_id):
            raise ValueError("invalid owner")
        if not authorize(Actor.MEMBER,Capability.MANAGE_OWN_MEMORY).allowed:
            return ()
        with locked(dsn) as (conn,_,now):
            consent = active_consent(conn,member_id,now)
            if not consent:
                return ()
            rows = conn.execute(
                """SELECT id,preference FROM member_memory WHERE member_id=%s AND epoch=%s
                   ORDER BY created_at,id LIMIT %s""",
                (member_id,consent["epoch"],MAX_MEMBER_MEMORIES),
            ).fetchall()
            return tuple(MemberPreference(row["id"],row["preference"]) for row in rows)
    except Exception as exc:
        logger.error("Member preference read failed (%s)",type(exc).__name__)
        raise


def delete_preference(dsn, member_id, memory_id):
    """Owner deletion works without active consent or canonical identity."""
    try:
        if not _valid_id(member_id) or not _valid_id(memory_id):
            raise ValueError("invalid owner or memory ID")
        if not authorize(Actor.MEMBER,Capability.WITHDRAW_MEMORY_CONSENT).allowed:
            return False
        with locked(dsn) as (conn,_,__):
            return conn.execute("DELETE FROM member_memory WHERE member_id=%s AND id=%s RETURNING id",
                                (member_id,memory_id)).fetchone() is not None
    except Exception as exc:
        logger.error("Member preference deletion failed (%s)",type(exc).__name__)
        raise
