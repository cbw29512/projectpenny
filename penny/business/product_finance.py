"""Attribute already-recorded financial evidence, never create revenue."""
import logging
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id,_valid_ref
from penny.scheduler.storage_db import locked

logger=logging.getLogger(__name__)
ELIGIBLE=("commercial_receipt","commercial_refund","operating_expense",
          "payment_fee","founder_paid_expense")


def attribute(dsn,product_id,entry_id,*,reviewer_id,evidence_ref,evidence,confirmed):
    """Full-entry attribution only; no split, transfer or new ledger event."""
    try:
        decision=authorize(Actor.ADMIN,Capability.ATTRIBUTE_PRODUCT_FINANCE)
        if not decision.allowed:
            return False
        if (confirmed is not True or not all(_valid_id(x) for x in
                (product_id,entry_id,reviewer_id)) or not _valid_ref(evidence_ref)):
            raise ValueError("invalid financial attribution")
        mark=fingerprint(entry_id,evidence)
        with locked(dsn) as (conn,_,now):
            entry=conn.execute("SELECT kind,reversal_of FROM vault_entry WHERE id=%s",
                               (entry_id,)).fetchone()
            if entry is None or entry["reversal_of"] is not None or entry["kind"] not in ELIGIBLE:
                return False
            if not conn.execute("SELECT 1 FROM business_product WHERE id=%s",(product_id,)).fetchone():
                return False
            old=conn.execute("SELECT * FROM business_product_finance WHERE entry_id=%s",
                             (entry_id,)).fetchone()
            fields=("product_id","reviewer_id","evidence_ref","evidence_sha256","evidence_size")
            values=(product_id,reviewer_id,evidence_ref,mark.digest,mark.byte_count)
            if old:
                if tuple(old[k] for k in fields)!=values:
                    raise ValueError("conflicting financial attribution")
                return True
            conn.execute("""INSERT INTO business_product_finance
                (entry_id,product_id,reviewer_id,evidence_ref,evidence_sha256,
                 evidence_size,recorded_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (entry_id,*values,now,decision.policy_version))
            return True
    except Exception as exc:
        logger.error("Product financial attribution refused (%s)",type(exc).__name__)
        raise


def summarize_product(dsn,product_id):
    try:
        if not _valid_id(product_id):
            raise ValueError("invalid product identifier")
        if not authorize(Actor.ADMIN,Capability.ATTRIBUTE_PRODUCT_FINANCE).allowed:
            return None
        with locked(dsn) as (conn,_,now):
            if not conn.execute("SELECT 1 FROM business_product WHERE id=%s",(product_id,)).fetchone():
                return None
            rows=conn.execute("""SELECT j.kind,count(*) AS n,
                sum(CASE WHEN j.reversal_of IS NULL THEN j.cents ELSE -j.cents END) AS net
                FROM vault_entry j JOIN business_product_finance a
                ON a.entry_id=coalesce(j.reversal_of,j.id)
                WHERE a.product_id=%s GROUP BY j.kind""",(product_id,)).fetchall()
            totals={r["kind"]:int(r["net"]) for r in rows}
            count=sum(r["n"] for r in rows)
            get=lambda k:totals.get(k,0)
            result=None if not count else {
                "commercial_receipts":get("commercial_receipt"),
                "refunds":get("commercial_refund"),
                "direct_costs":get("operating_expense")+get("founder_paid_expense"),
                "fees":get("payment_fee"),
                "recorded_direct_result":get("commercial_receipt")-get("commercial_refund")
                    -get("operating_expense")-get("founder_paid_expense")-get("payment_fee")}
            return {"status":"attributed_unreconciled" if count else "unavailable",
                    "currency":"USD","unit":"minor","as_of":now,"entry_count":count,
                    "result":result}
    except Exception as exc:
        logger.error("Product financial summary unavailable (%s)",type(exc).__name__)
        raise
