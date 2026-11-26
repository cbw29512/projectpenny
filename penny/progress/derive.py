"""Only aggregate existing reviewed source records under the scheduler lock."""
from penny.vault.budget import _matched
from penny.vault.summary import summary_locked
from penny.business.store import LATEST
from .state import SCHEMA,BUSINESS_KEYS,FINANCE_KEYS,validate


def derive(conn,now,*,finance,business):
    # Disclosing any section requires an explicit operator choice.
    financial=None
    if finance:
        match=_matched(conn,now)
        if match is not None:
            penny=summary_locked(conn,now)["penny"]
            if penny is not None:
                financial={k:penny[k] for k in FINANCE_KEYS
                           if k not in ("matched_cash","statement_at")}
                financial.update(matched_cash=match["observed_cash"],
                                 statement_at=match["statement_at"])
            elif match["penny_entry_count"]==0 and match["observed_cash"]==0:
                # Explicit reviewed zero cash/history coverage; not missing data.
                financial={k:0 for k in FINANCE_KEYS}
                financial["statement_at"]=match["statement_at"]
    ventures=None
    if business:
        rows=conn.execute("""SELECT CASE
            WHEN action='measured' THEN CASE WHEN measured_count>=target
                 THEN 'measured_target_met' ELSE 'measured_target_missed' END
            WHEN action='started' AND deadline<=%s THEN 'overdue'
            WHEN (action IS NULL OR action='approved') AND review_until<=%s THEN 'expired'
            ELSE coalesce(action,'proposed') END AS state,count(*) AS n
            FROM ("""+LATEST+""") AS x GROUP BY 1""",(now,now)).fetchall()
        if rows:
            ventures={k:0 for k in BUSINESS_KEYS}
            for row in rows:
                ventures[row["state"]]=row["n"]
    return validate({"schema":SCHEMA,"finance":financial,"business":ventures})
