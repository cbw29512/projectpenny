"""Private manual reconciliation. Never treat a match as available-to-spend cash."""
import logging
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id, _valid_ref
from penny.scheduler.storage_db import locked
from .state import MAX_CENTS, JournalReceipt

logger=logging.getLogger(__name__)
MAX_AGE=86400  # Conservative beta default; administrator policy still pending.


def _ledger(conn):
    # Founder-only events cannot invalidate Penny's own financial snapshot.
    row=conn.execute("""SELECT count(*) AS n,coalesce(max(occurred_at),0) AS latest
        FROM vault_entry WHERE kind NOT IN ('founder_income','founder_expense')""").fetchone()
    cash=conn.execute("""SELECT coalesce(sum(debit_minor),0) AS cash
        FROM vault_posting WHERE account='penny.cash'""").fetchone()
    return row["n"],row["latest"],int(cash["cash"])


def reconcile(dsn, *, source_ref, statement_at, observed_cash, evidence_ref,
              evidence, reviewer_id, coverage_confirmed):
    """Human attests complete dedicated cash scope and opening history."""
    try:
        decision=authorize(Actor.ADMIN,Capability.RECONCILE_VAULT)
        if not decision.allowed:
            return None
        if (not _valid_ref(source_ref) or not _valid_ref(evidence_ref)
                or not _valid_id(reviewer_id) or coverage_confirmed is not True
                or type(statement_at) is not int or statement_at<=0
                or type(observed_cash) is not int or not 0<=observed_cash<=MAX_CENTS):
            raise ValueError("invalid reconciliation")
        entry_id=uuid4()
        mark=fingerprint(entry_id,evidence)
        with locked(dsn) as (conn,_,now):
            if statement_at>now:
                raise ValueError("future statement")
            old=conn.execute("SELECT * FROM vault_reconciliation WHERE source_ref=%s",
                             (source_ref,)).fetchone()
            expected=(statement_at,observed_cash,evidence_ref,mark.digest,
                      mark.byte_count,reviewer_id,coverage_confirmed)
            if old:
                fields=("statement_at","observed_cash","evidence_ref","evidence_sha256",
                        "evidence_size","reviewer_id","coverage_confirmed")
                if tuple(old[k] for k in fields)!=expected:
                    raise ValueError("conflicting reconciliation source")
                return JournalReceipt(old["id"],True)
            n,latest,cash=_ledger(conn)
            # Statement must cover all recorded events. An old statement cannot
            # replace a newer reconciliation, even when the amounts happen to match.
            prev=conn.execute("""SELECT statement_at FROM vault_reconciliation
                ORDER BY sequence DESC LIMIT 1""").fetchone()
            if statement_at<latest or (prev and statement_at<prev["statement_at"]):
                raise ValueError("statement does not cover current ledger")
            conn.execute("""INSERT INTO vault_reconciliation
                (id,source_ref,statement_at,recorded_at,penny_entry_count,
                 ledger_cash,observed_cash,evidence_ref,evidence_sha256,
                 evidence_size,reviewer_id,policy_version,coverage_confirmed)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (entry_id,source_ref,statement_at,now,n,cash,observed_cash,
                 evidence_ref,mark.digest,mark.byte_count,reviewer_id,
                 decision.policy_version,True))
            return JournalReceipt(entry_id)
    except Exception as exc:
        logger.error("Vault reconciliation refused (%s)",type(exc).__name__)
        raise


def reconciliation_status(dsn):
    """Private aggregate; matched is a historical attestation, not a live balance."""
    try:
        with locked(dsn) as (conn,_,now):
            n,latest,cash=_ledger(conn)
            row=conn.execute("""SELECT * FROM vault_reconciliation
                ORDER BY sequence DESC LIMIT 1""").fetchone()
            base={"currency":"USD","unit":"minor","as_of":now,
                  "recorded_cash":cash if n else None,"matched_cash":None}
            if not row:
                return {**base,"status":"unavailable","statement_at":None,
                        "difference":None}
            observed=row["observed_cash"]
            difference=observed-int(row["ledger_cash"])
            if n!=row["penny_entry_count"] or cash!=row["ledger_cash"] or latest>row["statement_at"]:
                state="ledger_changed"
            elif difference!=0:
                state="mismatch"
            elif now<row["statement_at"] or now-row["statement_at"]>=MAX_AGE:
                state="stale"
            else:
                state="matched"
            return {**base,"status":state,"statement_at":row["statement_at"],
                    "difference":difference,
                    "matched_cash":observed if state=="matched" else None}
    except Exception as exc:
        logger.error("Vault reconciliation status unavailable (%s)",type(exc).__name__)
        raise
