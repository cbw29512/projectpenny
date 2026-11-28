"""Explicit administrator planning ceiling; never execute purchases."""
import logging
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id, _valid_ref
from penny.scheduler.storage_db import locked
from .reconciliation import _ledger, MAX_AGE
from .state import MAX_CENTS

logger=logging.getLogger(__name__)


def _matched(conn,now):
    row=conn.execute("SELECT * FROM vault_reconciliation ORDER BY sequence DESC LIMIT 1").fetchone()
    if not row:
        return None
    n,latest,cash=_ledger(conn)
    if (n!=row["penny_entry_count"] or latest>row["statement_at"]
            or cash!=row["ledger_cash"] or cash!=row["observed_cash"]
            or not 0<=now-row["statement_at"]<MAX_AGE):
        return None
    return row


def _budget(conn,now):
    row=conn.execute("SELECT * FROM vault_budget_review ORDER BY sequence DESC LIMIT 1").fetchone()
    held=int(conn.execute("""SELECT coalesce(sum(q.cents),0) AS held
        FROM vault_reservation r JOIN vault_spend_request q ON q.id=r.request_id
        LEFT JOIN vault_reservation_release x ON x.request_id=r.request_id
        WHERE x.request_id IS NULL""").fetchone()["held"])
    match=_matched(conn,now)
    # A new ledger event or reconciliation invalidates the prior ceiling.
    valid=(row is not None and match is not None and row["reconciliation_id"]==match["id"]
           and row["reviewed_at"]<=now<row["expires_at"])
    capacity=0
    if valid:
        capacity=max(0,min(row["ceiling_cents"],match["observed_cash"]-
                           row["obligations_cents"]-row["reserve_cents"])-held)
    return row,held,capacity,valid


def review_budget(dsn, *, reconciliation_id, ceiling_cents, obligations_cents,
                  reserve_cents, expires_at, reviewer_id, evidence_ref, evidence,
                  confirmed):
    """Administrator attests full obligations, restricted funds and owner consent."""
    try:
        decision=authorize(Actor.ADMIN,Capability.REVIEW_VAULT_BUDGET)
        if not decision.allowed:
            return None
        if (confirmed is not True or not _valid_id(reviewer_id)
                or not _valid_id(reconciliation_id) or not _valid_ref(evidence_ref)
                or type(expires_at) is not int
                or any(type(x) is not int or not 0<=x<=MAX_CENTS for x in
                       (ceiling_cents,obligations_cents,reserve_cents))):
            raise ValueError("invalid budget review")
        key=uuid4()
        mark=fingerprint(key,evidence)
        with locked(dsn) as (conn,_,now):
            match=_matched(conn,now)
            if (match is None or match["id"]!=reconciliation_id
                    or not now<expires_at<=match["statement_at"]+MAX_AGE):
                raise ValueError("fresh matching reconciliation required")
            if ceiling_cents>max(0,match["observed_cash"]-obligations_cents-reserve_cents):
                raise ValueError("ceiling exceeds reviewed cash")
            conn.execute("""INSERT INTO vault_budget_review
                (id,reconciliation_id,ceiling_cents,obligations_cents,reserve_cents,
                 reviewed_at,expires_at,reviewer_id,evidence_ref,evidence_sha256,evidence_size,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (key,reconciliation_id,ceiling_cents,obligations_cents,reserve_cents,
                 now,expires_at,reviewer_id,evidence_ref,mark.digest,mark.byte_count,decision.policy_version))
            return key
    except Exception as exc:
        logger.error("Budget review refused (%s)",type(exc).__name__)
        raise


def budget_status(dsn):
    try:
        with locked(dsn) as (conn,_,now):
            row,held,capacity,valid=_budget(conn,now)
            return {"status":"reviewed" if valid else "closed",
                    "budget_id":row["id"] if valid else None,
                    "planning_capacity_cents":capacity,"reserved_cents":held,
                    "authorized_cents":0}
    except Exception as exc:
        logger.error("Budget status unavailable (%s)",type(exc).__name__)
        raise
