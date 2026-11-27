"""Private approval of bounded beta previews; no public publication or sale."""
import hashlib
import json
import logging
import unicodedata
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id, _valid_ref
from penny.scheduler.storage_db import locked
from penny.vault.state import JournalReceipt
from .workshop_intake import read_locked
from .quality import _latest
from .store import _text

logger = logging.getLogger(__name__)
MAX_AGE = 604800
MAX_ACTIVE = 20
MAX_RECORDS = 4096


def _digest(title, text):
    return hashlib.sha256(json.dumps([title,text],ensure_ascii=False,
        separators=(",",":")).encode("utf-8")).hexdigest()


def _valid_preview(title,text):
    return (_text(title,120) and type(text) is str and 1<=len(text)<=2000
            and bool(text.strip()) and not any(
                unicodedata.category(c).startswith("C") and c!="\n"
                for c in title+text))


def _source_ok(conn,task,digest,now):
    artifact=read_locked(conn,task,now)
    review=_latest(conn,task)
    return bool(artifact and artifact["status"]=="private_prototype"
                and artifact["artifact"]["content_sha256"]==digest
                and not (review and review["revoked"]))


def approve(dsn,task_id,*,source_ref,artifact_sha256,title,preview_text,
            reviewer_id,evidence_ref,evidence,expires_at,confirmed):
    """Maker reviews exact excerpt and provenance separately from product quality."""
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_PRODUCT_CATALOG)
        if not decision.allowed:
            return None
        if (confirmed is not True or not _valid_id(task_id)
                or not _valid_id(reviewer_id) or not _valid_ref(source_ref)
                or not _valid_ref(evidence_ref) or not _valid_preview(title,preview_text)
                or type(artifact_sha256) is not str or len(artifact_sha256)!=64
                or type(expires_at) is not int):
            raise ValueError("invalid preview review")
        key=uuid4()
        mark=fingerprint(key,evidence)
        fields=("task_id","artifact_sha256","title","preview_text","preview_sha256",
                "reviewer_id","expires_at","evidence_ref","evidence_sha256","evidence_size")
        values=(task_id,artifact_sha256,title,preview_text,_digest(title,preview_text),
                reviewer_id,expires_at,evidence_ref,mark.digest,mark.byte_count)
        with locked(dsn) as (conn,_,now):
            prior=conn.execute("SELECT * FROM workshop_preview WHERE source_ref=%s",
                               (source_ref,)).fetchone()
            if prior:
                if tuple(prior[k] for k in fields)!=values:
                    raise ValueError("conflicting preview review")
                return JournalReceipt(prior["id"],True)
            if not now<expires_at<=now+MAX_AGE or not _source_ok(conn,task_id,artifact_sha256,now):
                return None
            counts=conn.execute("""SELECT count(*) AS total,
                count(*) FILTER (WHERE p.expires_at>%s AND w.preview_id IS NULL) AS active,
                count(*) FILTER (WHERE p.task_id=%s AND p.expires_at>%s
                    AND w.preview_id IS NULL) AS same_task
                FROM workshop_preview p LEFT JOIN workshop_preview_withdrawal w
                ON w.preview_id=p.id""",(now,task_id,now)).fetchone()
            if counts["total"]>=MAX_RECORDS or counts["active"]>=MAX_ACTIVE or counts["same_task"]:
                return None
            conn.execute("""INSERT INTO workshop_preview
                (id,source_ref,task_id,artifact_sha256,title,preview_text,preview_sha256,
                 reviewer_id,expires_at,evidence_ref,evidence_sha256,evidence_size,
                 reviewed_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (key,source_ref,*values,now,decision.policy_version))
            return JournalReceipt(key)
    except Exception as exc:
        logger.error("Preview approval refused (%s)",type(exc).__name__)
        raise


def read_preview_locked(conn,preview_id,now):
    """Trusted internal check; caller already holds scheduler lock."""
    p=conn.execute("""SELECT p.*,w.preview_id AS withdrawn
        FROM workshop_preview p LEFT JOIN workshop_preview_withdrawal w
        ON w.preview_id=p.id WHERE p.id=%s""",(preview_id,)).fetchone()
    if (not p or p["withdrawn"] or p["expires_at"]<=now
            or not _valid_preview(p["title"],p["preview_text"])
            or p["preview_sha256"]!=_digest(p["title"],p["preview_text"])
            or not _source_ok(conn,p["task_id"],p["artifact_sha256"],now)):
        return None
    return {"preview_id":str(preview_id),"title":p["title"],
            "preview_text":p["preview_text"],"preview_sha256":p["preview_sha256"],
            "expires_at":p["expires_at"],"status":"beta_feedback_only",
            "commercial_release_authorized":False}


def read_preview(dsn,preview_id):
    """Trusted local projection candidate only; no public endpoint or owner data."""
    try:
        if not _valid_id(preview_id):
            raise ValueError("invalid preview ID")
        if not authorize(Actor.ADMIN,Capability.REVIEW_PRODUCT_CATALOG).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            return read_preview_locked(conn,preview_id,now)
    except Exception as exc:
        logger.error("Preview read refused (%s)",type(exc).__name__)
        raise


def withdraw(dsn,preview_id,*,reviewer_id,evidence_ref,evidence,confirmed):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_PRODUCT_CATALOG)
        if not decision.allowed:
            return False
        if (confirmed is not True or not _valid_id(preview_id)
                or not _valid_id(reviewer_id) or not _valid_ref(evidence_ref)):
            raise ValueError("invalid preview withdrawal")
        mark=fingerprint(preview_id,evidence)
        with locked(dsn) as (conn,_,now):
            if not conn.execute("SELECT 1 FROM workshop_preview WHERE id=%s",
                                (preview_id,)).fetchone():
                return False
            return conn.execute("""INSERT INTO workshop_preview_withdrawal
                VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING preview_id""",
                (preview_id,reviewer_id,now,evidence_ref,mark.digest,mark.byte_count,
                 decision.policy_version)).fetchone() is not None
    except Exception as exc:
        logger.error("Preview withdrawal refused (%s)",type(exc).__name__)
        raise
