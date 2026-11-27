"""Select exact reviewed private product evidence, never arbitrary public text."""
import json
from hashlib import sha256
from penny.business.catalog import _ready
from penny.business.preview import read_preview_locked
from penny.business.revision_review import status_locked

SCHEMA="penny-workshop-v1"
PRODUCT="packing-checklist-v1"
TITLE="Penny's Minimalist Traveler's 7-Day Packing Checklist"
STAGES=frozenset(("prototype_reviewed","preview_reviewed","revision_reviewed","review_withdrawn"))
MAX_AGE=3600


def unavailable():
    return {"schema":SCHEMA,"status":"unavailable"}


def source_locked(conn,product_id,stage,preview_id,now):
    row=conn.execute("""SELECT p.*,x.recorded_at AS withdrawn_at,
        x.evidence_sha256 AS withdrawal_sha256 FROM business_product p
        LEFT JOIN business_product_withdrawal x ON x.product_id=p.id
        WHERE p.id=%s""",(product_id,)).fetchone()
    if not row or row["title"]!=TITLE or row["created_at"]>now:
        return None
    data={"product_id":str(product_id),"task_id":str(row["task_id"]),
          "quality_review_id":str(row["quality_review_id"]),"content_sha256":row["content_sha256"],
          "stage":stage}
    expiry=None
    if preview_id is not None:
        p=conn.execute("""SELECT p.*,w.recorded_at AS withdrawn_at,
            w.evidence_sha256 AS withdrawal_sha256 FROM workshop_preview p
            LEFT JOIN workshop_preview_withdrawal w ON w.preview_id=p.id
            WHERE p.id=%s""",(preview_id,)).fetchone()
        if not p or p["task_id"]!=row["task_id"] or p["artifact_sha256"]!=row["content_sha256"]:
            return None
        data.update(preview_id=str(preview_id),preview_sha256=p["preview_sha256"])
    if stage=="review_withdrawn":
        withdrawn=row["withdrawn_at"] if preview_id is None else p["withdrawn_at"]
        if withdrawn is None or withdrawn>now:
            return None
        data.update(withdrawn_at=withdrawn,withdrawal_sha256=(
            row["withdrawal_sha256"] if preview_id is None else p["withdrawal_sha256"]))
    else:
        if row["withdrawn_at"] is not None or not _ready(
                conn,row["task_id"],row["quality_review_id"],row["content_sha256"],now):
            return None
        if stage=="preview_reviewed":
            projection=read_preview_locked(conn,preview_id,now)
            if projection is None:
                return None
            expiry=projection["expires_at"]
            data["preview_expires_at"]=expiry
        elif stage=="revision_reviewed":
            status=status_locked(conn,row["task_id"],now)
            if not status or not status["improvement_verified"]:
                return None
            review=conn.execute("""SELECT r.basis_sha256,r.evidence_sha256,p.expires_at
                FROM workshop_revision_review r JOIN workshop_revision w ON w.task_id=r.task_id
                JOIN workshop_preview p ON p.id=w.preview_id WHERE r.task_id=%s""",
                (row["task_id"],)).fetchone()
            expiry=review["expires_at"]
            data.update(basis_sha256=review["basis_sha256"],review_evidence_sha256=review["evidence_sha256"])
    return sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest(),expiry
