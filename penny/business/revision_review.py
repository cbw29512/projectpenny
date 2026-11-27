"""Private evidence-based revision verdict; not a quality or release override."""
import logging
import re

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked
from .quality import _latest,_verdict
from .revision_compare import compare_locked

logger=logging.getLogger(__name__)


def review_revision(dsn,task_id,*,parent_sha256,child_sha256,basis_sha256,
                    quality_review_id,verdict,reviewer_id,evidence_ref,evidence,confirmed):
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT)
        if not decision.allowed:
            return False
        if (confirmed is not True or not all(_valid_id(x) for x in
                (task_id,quality_review_id,reviewer_id)) or not _valid_ref(evidence_ref)
                or verdict not in ("improved","not_improved")
                or any(type(x) is not str or not re.fullmatch(r"[a-f0-9]{64}",x)
                       for x in (parent_sha256,child_sha256,basis_sha256))):
            raise ValueError("invalid revision verdict")
        mark=fingerprint(task_id,evidence)
        fields=("parent_sha256","child_sha256","basis_sha256","quality_review_id",
                "verdict","reviewer_id","evidence_ref","evidence_sha256","evidence_size")
        values=(parent_sha256,child_sha256,basis_sha256,quality_review_id,
                verdict,reviewer_id,evidence_ref,mark.digest,mark.byte_count)
        with locked(dsn) as (conn,_,now):
            old=conn.execute("SELECT * FROM workshop_revision_review WHERE task_id=%s",
                             (task_id,)).fetchone()
            if old:
                # Exact retry is a historical receipt, not current validation.
                return tuple(old[k] for k in fields)==values
            comparison=compare_locked(conn,task_id,now)
            quality=_latest(conn,task_id)
            if (not comparison or comparison["status"]!="available" or not quality
                    or quality["id"]!=quality_review_id
                    or quality["content_sha256"]!=child_sha256
                    or _verdict(quality) not in ("passed","failed")
                    or (comparison["before"]["sha256"],comparison["after"]["sha256"],
                        comparison["basis_sha256"])!=(parent_sha256,child_sha256,basis_sha256)):
                return False
            if verdict=="improved" and (not comparison["basis_current"]
                    or not comparison["comparison"]["content_changed"]
                    or comparison["before"]["quality_status"] in ("revoked","unavailable")
                    or comparison["after"]["quality_status"]!="passed"):
                return False
            conn.execute("""INSERT INTO workshop_revision_review
                (task_id,parent_sha256,child_sha256,basis_sha256,quality_review_id,
                 verdict,reviewer_id,evidence_ref,evidence_sha256,evidence_size,
                 reviewed_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (task_id,*values,now,decision.policy_version))
            return True
    except Exception as exc:
        logger.error("Revision verdict refused (%s)",type(exc).__name__)
        raise


def revision_review_status(dsn,task_id):
    """Private status; stale evidence never becomes a current improvement claim."""
    try:
        if not _valid_id(task_id):
            raise ValueError("invalid revision task")
        if not authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            comparison=compare_locked(conn,task_id,now)
            if comparison is None:
                return None
            row=conn.execute("SELECT * FROM workshop_revision_review WHERE task_id=%s",
                             (task_id,)).fetchone()
            base={"commercial_release_authorized":False,"improvement_verified":False,
                  "recorded_verdict":row["verdict"] if row else None}
            if not row:
                return base|{"status":"unreviewed"}
            quality=_latest(conn,task_id)
            current=(comparison["status"]=="available" and quality is not None
                     and quality["id"]==row["quality_review_id"]
                     and comparison["before"]["sha256"]==row["parent_sha256"]
                     and comparison["after"]["sha256"]==row["child_sha256"]
                     and comparison["basis_sha256"]==row["basis_sha256"]
                     and comparison["basis_current"]
                     and comparison["before"]["quality_status"] not in ("revoked","unavailable")
                     and comparison["after"]["quality_status"] in ("passed","failed"))
            verified=bool(current and row["verdict"]=="improved"
                          and comparison["after"]["quality_status"]=="passed"
                          and comparison["comparison"]["content_changed"])
            return base|{"status":row["verdict"] if current else "stale",
                         "improvement_verified":verified}
    except Exception as exc:
        logger.error("Revision verdict status unavailable (%s)",type(exc).__name__)
        raise
