"""Bind reviewed model output to a private opportunity in one transaction."""
import logging
import re
from hashlib import sha256
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked
from .draft_parse import parse_draft
from .draft_state import DRAFT_PREFIX
from .state import MAX_REVIEW
from .store import PROMOTED_PREFIX,stage_locked

logger=logging.getLogger(__name__)
FIELDS=("category","title","hypothesis","metric","target","duration_seconds",
        "additional_cash_cents","evidence_ref","evidence_sha256","evidence_size",
        "reviewer_id","review_until")


def promote(dsn,task_id,*,expected_result_sha256,evidence_ref,evidence,
            reviewer_id,review_until,confirmed):
    """Review of independent evidence only; promotion is not approval to start."""
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_BUSINESS_EXPERIMENT)
        if not decision.allowed:
            return None
        if (not _valid_id(task_id) or not _valid_id(reviewer_id)
                or not _valid_ref(evidence_ref) or confirmed is not True
                or type(review_until) is not int
                or type(expected_result_sha256) is not str
                or not re.fullmatch(r"[a-f0-9]{64}",expected_result_sha256)):
            raise ValueError("invalid draft promotion review")
        key=uuid4()
        mark=fingerprint(key,evidence)
        with locked(dsn) as (conn,_,now):
            row=conn.execute("""SELECT c.*,o.result,o.finished_at,t.idempotency_key
                FROM business_draft_candidate c
                JOIN business_draft_task d ON d.task_id=c.task_id
                JOIN work_task t ON t.id=d.task_id
                JOIN task_outcome o ON o.task_id=t.id
                WHERE c.task_id=%s AND t.member_id IS NULL
                  AND t.state='succeeded' AND o.status='succeeded'""",(task_id,)).fetchone()
            if (row is None or not row["idempotency_key"].startswith(DRAFT_PREFIX)
                    or row["result_sha256"]!=expected_result_sha256
                    or sha256(row["result"].encode("utf-8")).hexdigest()!=expected_result_sha256):
                return None
            draft=parse_draft(row["result"])
            if draft is None:
                return None
            shape=(draft.category.value,draft.title,draft.hypothesis,draft.metric.value,
                   draft.target,draft.duration_seconds,draft.additional_cash_cents)
            if tuple(row[k] for k in FIELDS[:7])!=shape:
                return None
            values=(*shape,evidence_ref,mark.digest,mark.byte_count,reviewer_id,review_until)
            source_ref=PROMOTED_PREFIX+str(task_id)
            previous=conn.execute("SELECT * FROM business_draft_promotion WHERE task_id=%s",
                                  (task_id,)).fetchone()
            if previous is None:
                # No new promotion of stale or future-dated inference results.
                if not 0<=now-row["finished_at"]<MAX_REVIEW:
                    return None
                if conn.execute("SELECT 1 FROM business_opportunity WHERE source_ref=%s",
                                (source_ref,)).fetchone():
                    raise ValueError("unlinked reserved source")
            receipt=stage_locked(conn,now,key,source_ref,FIELDS,values,
                                 review_until,decision.policy_version)
            if receipt is None:
                return None
            if previous is not None:
                if (previous["opportunity_id"]!=receipt.entry_id
                        or previous["result_sha256"]!=expected_result_sha256
                        or previous["reviewer_id"]!=reviewer_id):
                    raise ValueError("conflicting promotion")
                return receipt
            conn.execute("INSERT INTO business_draft_promotion VALUES (%s,%s,%s,%s,%s,%s)",
                         (task_id,receipt.entry_id,expected_result_sha256,reviewer_id,
                          now,decision.policy_version))
            return receipt
    except Exception as exc:
        logger.error("Business draft promotion refused (%s)",type(exc).__name__)
        raise
