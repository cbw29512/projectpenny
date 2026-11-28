"""Private product registration, exact artifact review and withdrawal."""
import logging
from uuid import uuid4
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked
from penny.vault.state import JournalReceipt
from .quality import _latest,_verdict
from .store import _text
from .workshop_intake import read_locked

logger=logging.getLogger(__name__)


def _ready(conn,task_id,review_id,digest,now):
    current=_latest(conn,task_id)
    if (_verdict(current)!="passed" or current["id"]!=review_id
            or current["content_sha256"]!=digest):
        return False
    artifact=read_locked(conn,task_id,now)
    return bool(artifact and artifact["status"]=="private_prototype"
                and artifact["artifact"]["content_sha256"]==digest)


def register(dsn,task_id,*,source_ref,review_id,content_sha256,title,
             reviewer_id,evidence_ref,evidence,confirmed):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_PRODUCT_CATALOG)
        if not decision.allowed:
            return None
        if (confirmed is not True or not all(_valid_id(v) for v in
                (task_id,review_id,reviewer_id)) or not _valid_ref(source_ref)
                or not _valid_ref(evidence_ref) or not _text(title,120)
                or type(content_sha256) is not str or len(content_sha256)!=64):
            raise ValueError("invalid catalog review")
        key=uuid4()
        mark=fingerprint(key,evidence)
        fields=("task_id","quality_review_id","content_sha256","title","reviewer_id",
                "evidence_ref","evidence_sha256","evidence_size")
        values=(task_id,review_id,content_sha256,title,reviewer_id,evidence_ref,
                mark.digest,mark.byte_count)
        with locked(dsn) as (conn,_,now):
            old=conn.execute("SELECT * FROM business_product WHERE source_ref=%s",
                             (source_ref,)).fetchone()
            if old:
                if tuple(old[k] for k in fields)!=values:
                    raise ValueError("conflicting catalog source")
                return JournalReceipt(old["id"],True)
            if conn.execute("SELECT 1 FROM business_product WHERE task_id=%s",(task_id,)).fetchone():
                return None
            if not _ready(conn,task_id,review_id,content_sha256,now):
                return None
            conn.execute("""INSERT INTO business_product
                (id,source_ref,task_id,quality_review_id,content_sha256,title,reviewer_id,
                 evidence_ref,evidence_sha256,evidence_size,created_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (key,source_ref,*values,now,decision.policy_version))
            return JournalReceipt(key)
    except Exception as exc:
        logger.error("Product registration refused (%s)",type(exc).__name__)
        raise


def withdraw(dsn,product_id,*,reviewer_id,evidence_ref,evidence,confirmed):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_PRODUCT_CATALOG)
        if not decision.allowed:
            return False
        if (confirmed is not True or not _valid_id(product_id)
                or not _valid_id(reviewer_id) or not _valid_ref(evidence_ref)):
            raise ValueError("invalid product withdrawal")
        mark=fingerprint(product_id,evidence)
        with locked(dsn) as (conn,_,now):
            if not conn.execute("SELECT 1 FROM business_product WHERE id=%s",(product_id,)).fetchone():
                return False
            return conn.execute("""INSERT INTO business_product_withdrawal VALUES
                (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(product_id) DO NOTHING RETURNING product_id""",
                (product_id,reviewer_id,now,evidence_ref,mark.digest,mark.byte_count,
                 decision.policy_version)).fetchone() is not None
    except Exception as exc:
        logger.error("Product withdrawal refused (%s)",type(exc).__name__)
        raise


def status(dsn,product_id):
    try:
        if not _valid_id(product_id):
            raise ValueError("invalid product identifier")
        if not authorize(Actor.ADMIN,Capability.REVIEW_PRODUCT_CATALOG).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            row=conn.execute("""SELECT p.*,w.opportunity_id,x.product_id AS withdrawn
                FROM business_product p JOIN workshop_task w ON w.task_id=p.task_id
                LEFT JOIN business_product_withdrawal x ON x.product_id=p.id
                WHERE p.id=%s""",(product_id,)).fetchone()
            if row is None:
                return None
            state="withdrawn" if row["withdrawn"] else "private_candidate" if _ready(
                conn,row["task_id"],row["quality_review_id"],row["content_sha256"],now) else "review_changed"
            return {"status":state,"title":row["title"],"opportunity_id":row["opportunity_id"],
                    "task_id":row["task_id"],"commercial_release_authorized":False}
    except Exception as exc:
        logger.error("Catalog status unavailable (%s)",type(exc).__name__)
        raise
