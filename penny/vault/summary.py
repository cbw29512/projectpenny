"""Private read model derived from posted evidence; not reconciled bank balances."""
import logging
from penny.scheduler.storage_db import locked

logger=logging.getLogger(__name__)


def summarize(dsn):
    try:
        with locked(dsn) as (conn,_,now):
            rows=conn.execute("""SELECT kind,count(*) AS n,
                sum(CASE WHEN reversal_of IS NULL THEN cents ELSE -cents END) AS net
                FROM vault_entry GROUP BY kind""").fetchall()
        totals={r["kind"]:int(r["net"]) for r in rows}
        count=sum(r["n"] for r in rows)
        def get(k): return totals.get(k,0)
        penny_present=any(not k.startswith("founder_") or k in
                          ("founder_paid_expense","founder_funding") for k in totals)
        founder_present=any(k in totals for k in ("founder_income","founder_expense"))
        commercial=get("commercial_receipt")-get("commercial_refund")
        expense=get("operating_expense")+get("founder_paid_expense")
        fees=get("payment_fee")
        cash=commercial+get("community_support")+get("founder_funding")-get("operating_expense")-fees
        return {
            "currency":"USD","unit":"minor","as_of":now,"entry_count":count,
            "status":"recorded_unreconciled" if count else "unavailable",
            "penny":None if not penny_present else {
                "commercial_receipts":get("commercial_receipt"),
                "commercial_refunds":get("commercial_refund"),
                "net_commercial_receipts":commercial,
                "community_support":get("community_support"),
                "founder_cash_funding":get("founder_funding"),
                "founder_paid_costs":get("founder_paid_expense"),
                "operating_expenses":expense,"payment_fees":fees,
                "commercial_result_after_recorded_costs":commercial-expense-fees,
                "recorded_cash":cash,
                "cash_discrepancy":cash<0,
            },
            "founder":None if not founder_present else {
                "attributed_income":get("founder_income"),
                "attributed_expense":get("founder_expense"),
                "recorded_net":get("founder_income")-get("founder_expense"),
            },
        }
    except Exception as exc:
        logger.error("Vault summary unavailable (%s)",type(exc).__name__)
        raise
