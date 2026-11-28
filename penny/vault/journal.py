"""Trusted administrator recording only; no funds movement."""
import logging
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id, _valid_ref
from penny.scheduler.storage_db import locked
from .state import Kind, MAX_CENTS, JournalReceipt

logger = logging.getLogger(__name__)


def record(dsn, *, source_ref, kind, cents, occurred_at, evidence_ref,
           evidence, reviewer_id, reversal_of=None):
    # This is an evidence attestation, NOT approval to spend money.
    try:
        decision=authorize(Actor.ADMIN,Capability.RECORD_VAULT_ENTRY)
        if not decision.allowed:
            return None
        if (not _valid_ref(source_ref) or not _valid_ref(evidence_ref)
                or not _valid_id(reviewer_id) or type(kind) is not Kind
                or type(cents) is not int or not 1<=cents<=MAX_CENTS
                or type(occurred_at) is not int or occurred_at<=0
                or (reversal_of is not None and not _valid_id(reversal_of))):
            raise ValueError("invalid journal event")
        entry_id=uuid4()
        mark=fingerprint(entry_id,evidence)
        with locked(dsn) as (conn,_,now):
            if occurred_at>now:
                raise ValueError("future financial event")
            previous=conn.execute("SELECT * FROM vault_entry WHERE source_ref=%s",
                                  (source_ref,)).fetchone()
            expected=(kind.value,cents,occurred_at,evidence_ref,mark.digest,
                      mark.byte_count,reviewer_id,reversal_of)
            if previous:
                fields=("kind","cents","occurred_at","evidence_ref","evidence_sha256",
                        "evidence_size","reviewer_id","reversal_of")
                if tuple(previous[k] for k in fields)!=expected:
                    raise ValueError("conflicting source reference")
                return JournalReceipt(previous["id"],True)
            if reversal_of is not None:
                original=conn.execute("SELECT * FROM vault_entry WHERE id=%s",
                                      (reversal_of,)).fetchone()
                if (original is None or original["reversal_of"] is not None
                        or original["kind"]!=kind.value or original["cents"]!=cents
                        or original["occurred_at"]>occurred_at):
                    raise ValueError("invalid reversal")
                if conn.execute("SELECT 1 FROM vault_entry WHERE reversal_of=%s",
                                (reversal_of,)).fetchone():
                    raise ValueError("already reversed")
            conn.execute(
                """INSERT INTO vault_entry
                   (id,source_ref,kind,cents,occurred_at,recorded_at,evidence_ref,
                    evidence_sha256,evidence_size,reviewer_id,policy_version,reversal_of)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (entry_id,source_ref,kind.value,cents,occurred_at,now,evidence_ref,
                 mark.digest,mark.byte_count,reviewer_id,decision.policy_version,reversal_of),
            )
            return JournalReceipt(entry_id)
    except Exception as exc:
        logger.error("Vault record refused (%s)",type(exc).__name__)
        raise
