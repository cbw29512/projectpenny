"""Exact-draft approval and durable delivery receipt; trusted callers only."""
from dataclasses import dataclass, field
import hashlib
import logging
from uuid import UUID

from penny.guardian.policy import authorize, APPROVED_PROMPT_SHA256, validate_draft
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from .receipts import valid_id
from .state import wire_text
from .reply_db import reply_call

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ApprovedReply:
    question_id: UUID
    fence: UUID
    draft_sha256: str
    text: str = field(repr=False)


def _digest(text):
    return hashlib.sha256(wire_text(text,16000).encode("utf-8")).hexdigest()


def _live(conn,question_id,now):
    return conn.execute(
        """SELECT r.question_id,r.fence,o.result,a.draft_sha256,a.identity_sha256,
                  a.delivered_at
        FROM bridge_receipt r JOIN bridge_member m
          ON m.cloud_owner=r.cloud_owner AND m.local_member=r.local_member AND m.enabled
        JOIN work_task t ON t.id=r.task_id AND t.member_id=r.local_member AND t.state='succeeded'
        JOIN task_outcome o ON o.task_id=t.id AND o.status='succeeded'
        LEFT JOIN bridge_release a ON a.question_id=r.question_id
        WHERE r.question_id=%s AND r.acked_at IS NOT NULL AND r.expires_at>%s
          AND r.remote_rejected_at IS NULL
        FOR UPDATE OF r,m,t,o""",(question_id,now)
    ).fetchone()


def approve_reply(dsn,question_id,*,reviewer_id,expected_text):
    # reviewer_id is a trusted local operator attestation, NOT external auth.
    try:
        if not valid_id(question_id) or not valid_id(reviewer_id):
            return False
        digest = _digest(expected_text)
    except (ValueError,TypeError):
        logger.warning("Bridge reply approval rejected")
        return False
    with locked(dsn) as (conn,control,now):
        if control["paused"] or not authorize(Actor.ADMIN,Capability.APPROVE_BRIDGE_REPLY).allowed:
            return False
        row = _live(conn,question_id,now)
        if row is None or row["result"] != expected_text or not validate_draft(expected_text).allowed:
            return False
        if row["draft_sha256"] is not None:
            return row["draft_sha256"] == digest and row["identity_sha256"] == APPROVED_PROMPT_SHA256
        conn.execute(
            """INSERT INTO bridge_release
            (question_id,draft_sha256,reviewer_id,identity_sha256,approved_at)
            VALUES (%s,%s,%s,%s,%s)""",
            (question_id,digest,reviewer_id,APPROVED_PROMPT_SHA256,now),
        )
        return True


def pending_reply(dsn,question_id):
    if not valid_id(question_id) or not authorize(
            Actor.WORKER,Capability.READ_APPROVED_BRIDGE_REPLY).allowed:
        return None
    row=reply_call(dsn,"pending",(question_id,))
    if row is None or not validate_draft(row["result"]).allowed:
        return None
    # Independent local digest check in addition to the DB approval boundary.
    if _digest(row["result"])!=row["draft_sha256"]:
        return None
    return ApprovedReply(question_id,row["fence"],row["draft_sha256"],row["result"])


def record_delivery(dsn,reply):
    # A confirmed external response is an attestation, not new authority.
    try:
        if (type(reply) is not ApprovedReply or not valid_id(reply.question_id)
                or not valid_id(reply.fence) or not authorize(
                    Actor.WORKER,Capability.READ_APPROVED_BRIDGE_REPLY).allowed
                or _digest(reply.text)!=reply.draft_sha256):
            return False
        row=reply_call(dsn,"delivered",(reply.question_id,reply.fence,reply.draft_sha256))
        return row is not None and row["recorded"] is True
    except (ValueError,TypeError):
        logger.warning("Mailbox delivery receipt rejected")
        return False
