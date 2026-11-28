"""Trusted local comparison of immutable checklist revisions; no approval."""
import json
import logging
from hashlib import sha256

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.review import _valid_id
from penny.scheduler.storage_db import locked
from .quality import _latest,_verdict
from .revision import _basis,PROMPT
from .workshop_intake import read_locked

logger=logging.getLogger(__name__)


def _parts(content):
    # The validated renderer produces exactly these newline-delimited fields.
    # Use literal LF, not splitlines(), which also splits Unicode separators.
    lines=content.split("\n")
    return lines[0],lines[2],[line[4:] for line in lines[4:-1]]


def _quality(conn,task,digest):
    row=_latest(conn,task)
    if row and row["content_sha256"]!=digest:
        return "unavailable"
    return _verdict(row)


def _compare(parent,child):
    old_title,old_instructions,old_items=_parts(parent)
    new_title,new_instructions,new_items=_parts(child)
    retained=[item for item in old_items if item in new_items]
    return {
        "title_changed":old_title!=new_title,
        "instructions_changed":old_instructions!=new_instructions,
        "added_items":[item for item in new_items if item not in old_items],
        "removed_items":[item for item in old_items if item not in new_items],
        "retained_items":retained,
        "retained_order_changed":retained!=[item for item in new_items if item in old_items],
        "before_item_count":len(old_items),"after_item_count":len(new_items),
        "content_changed":parent!=child,
    }


def compare_revision(dsn,task_id):
    """Inspect exact bytes and lineage together under the scheduler lock."""
    try:
        if not _valid_id(task_id):
            raise ValueError("invalid revision task")
        if not authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            return compare_locked(conn,task_id,now)
    except Exception as exc:
        logger.error("Workshop revision comparison failed (%s)",type(exc).__name__)
        raise


def compare_locked(conn,task_id,now):
    """Caller holds scheduler lock; never approve or publish."""
    link=conn.execute("""SELECT r.*,p.task_id AS preview_task,
        p.artifact_sha256 AS preview_parent_sha256,
        w.opportunity_id AS child_opportunity,
        parent.opportunity_id AS parent_opportunity,t.payload
        FROM workshop_revision r
        JOIN workshop_preview p ON p.id=r.preview_id
        JOIN workshop_task w ON w.task_id=r.task_id
        JOIN workshop_task parent ON parent.task_id=r.parent_task_id
        JOIN work_task t ON t.id=r.task_id WHERE r.task_id=%s""",(task_id,)).fetchone()
    if link is None:
        return None
    base={"task_id":str(task_id),"parent_task_id":str(link["parent_task_id"]),
          "commercial_release_authorized":False,"comparison":None}
    parent=read_locked(conn,link["parent_task_id"],now)
    child=read_locked(conn,task_id,now)
    if (not parent or parent["status"]!="private_prototype" or not child
            or link["preview_task"]!=link["parent_task_id"]
            or link["parent_opportunity"]!=link["child_opportunity"]
            or link["preview_parent_sha256"]!=link["parent_sha256"]
            or parent["artifact"]["content_sha256"]!=link["parent_sha256"]):
        return base|{"status":"integrity_error"}
    old=parent["artifact"]
    # Reconstruct the canonical admitted prompt and check its brief hash.
    # No arbitrary text from a corrupt task is returned to the operator.
    try:
        payload=link["payload"]
        if not payload.startswith(PROMPT):
            raise ValueError("missing revision prompt")
        data=json.loads(payload[len(PROMPT):])
        brief=data["reviewed_improvement"]
        if (type(brief) is not str or data["prior_checklist"]!=old["content"]
                or sha256(brief.encode()).hexdigest()!=link["brief_sha256"]
                or payload!=PROMPT+json.dumps({"prior_checklist":old["content"],
                    "reviewed_improvement":brief},ensure_ascii=False,separators=(",",":"))):
            raise ValueError("revision prompt mismatch")
    except (ValueError,TypeError,KeyError,RecursionError):
        return base|{"status":"integrity_error"}
    if child["status"]!="private_prototype":
        return base|{"status":child["status"]}
    new=child["artifact"]
    basis=_basis(conn,link["preview_id"],now)
    before_quality=_quality(conn,link["parent_task_id"],old["content_sha256"])
    after_quality=_quality(conn,task_id,new["content_sha256"])
    return base|{
        "status":"available","reviewed_improvement":brief,
        "basis_sha256":link["basis_sha256"],
        "basis_current":basis is not None and basis[2]==link["basis_sha256"],
        "before":{"content":old["content"],"sha256":old["content_sha256"],
                  "quality_status":before_quality},
        "after":{"content":new["content"],"sha256":new["content_sha256"],
                 "quality_status":after_quality},
        "comparison":_compare(old["content"],new["content"]),
        "improvement_verified":False,
    }
