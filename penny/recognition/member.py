"""Token-only private attribution opt-in, read and withdrawal."""
import logging
from uuid import uuid4

from penny.auth.session import resolve_member
from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.review import _valid_id
from penny.scheduler.storage_db import locked
from .messages import appreciation
from .workshop import credit_allowed_locked
from .state import CONSENT_VERSION, MAX_REQUESTS, Outcome, Role, Recognition

logger = logging.getLogger(__name__)


def request_credit(dsn,token,outcome_id,role,*,accepted_version):
    try:
        if not _valid_id(outcome_id) or type(role) is not Role or accepted_version != CONSENT_VERSION:
            raise ValueError("invalid private recognition consent")
        if not authorize(Actor.MEMBER,Capability.MANAGE_OWN_RECOGNITION).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            owner = resolve_member(conn,now,token)
            if not credit_allowed_locked(conn,outcome_id,owner,role.value,now):
                return None
            old = conn.execute(
                "SELECT id,consent_version,requested_at FROM contribution_request WHERE member_id=%s AND outcome_id=%s AND role=%s",
                (owner,outcome_id,role.value),
            ).fetchone()
            if old:
                # Historical consent cannot stand in for current, explicit consent.
                if old["consent_version"] != CONSENT_VERSION or not 0 <= old["requested_at"] <= now:
                    return None
                return old["id"]
            count = conn.execute("SELECT count(*) AS n FROM contribution_request WHERE member_id=%s",
                                 (owner,)).fetchone()["n"]
            if count >= MAX_REQUESTS:
                return None
            request_id = uuid4()
            conn.execute("INSERT INTO contribution_request VALUES (%s,%s,%s,%s,%s,%s)",
                         (request_id,owner,outcome_id,role.value,CONSENT_VERSION,now))
            return request_id
    except Exception as exc:
        logger.error("Private recognition request failed (%s)",type(exc).__name__)
        raise


def list_credit(dsn,token):
    try:
        if not authorize(Actor.MEMBER,Capability.MANAGE_OWN_RECOGNITION).allowed:
            return ()
        with locked(dsn) as (conn,_,now):
            owner = resolve_member(conn,now,token)
            rows = conn.execute(
                """SELECT q.id,q.outcome_id,q.role,o.verdict
                   FROM contribution_request q JOIN contribution_recognition c ON c.request_id=q.id
                   JOIN contribution_outcome o ON o.id=q.outcome_id
                   WHERE q.member_id=%s AND q.consent_version=%s
                   AND 0 <= o.recorded_at AND o.recorded_at <= q.requested_at
                   AND q.requested_at <= c.recorded_at AND c.recorded_at <= %s
                   ORDER BY c.recorded_at,q.id LIMIT %s""",
                (owner,CONSENT_VERSION,now,MAX_REQUESTS),
            ).fetchall()
            return tuple(Recognition(r["id"],r["outcome_id"],Role(r["role"]),Outcome(r["verdict"]),
                                     appreciation(Role(r["role"]),Outcome(r["verdict"]))) for r in rows
                         if credit_allowed_locked(conn,r["outcome_id"],owner,r["role"],now))
    except Exception as exc:
        logger.error("Private recognition read failed (%s)",type(exc).__name__)
        raise


def withdraw_credit(dsn,token,request_id):
    """Owner revokes private attribution; no new review can revive old consent ID."""
    try:
        if not _valid_id(request_id):
            raise ValueError("invalid recognition request")
        if not authorize(Actor.MEMBER,Capability.WITHDRAW_RECOGNITION).allowed:
            return False
        with locked(dsn) as (conn,_,now):
            owner = resolve_member(conn,now,token)
            return conn.execute(
                "DELETE FROM contribution_request WHERE id=%s AND member_id=%s RETURNING id",
                (request_id,owner),
            ).fetchone() is not None
    except Exception as exc:
        logger.error("Recognition withdrawal failed (%s)",type(exc).__name__)
        raise
