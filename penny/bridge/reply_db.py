"""Scoped mailbox calls; no raw task or approval table access."""
import logging

import psycopg
from psycopg.rows import dict_row

logger=logging.getLogger(__name__)
CALLS={
    "community_defer":"SELECT penny_community_defer(%s,%s) AS recorded",
    "community_recover":"SELECT * FROM penny_community_recover()",
    "community_record_ack":"SELECT penny_community_record_ack(%s,%s) AS recorded",
    "community_reserve":"SELECT penny_community_reserve() AS recorded",
    "community_verify":"SELECT penny_community_receipt_exists(%s,%s) AS recorded",
    "community_admit":"SELECT penny_community_admit(%s,%s,%s,%s,%s,%s,%s) AS recorded",
    "reserve":"SELECT * FROM penny_bridge_reserve()",
    "defer":"SELECT penny_bridge_defer(%s,%s) AS recorded",
    "reject":"SELECT penny_bridge_reject(%s,%s,%s) AS recorded",
    "admit":"SELECT * FROM penny_bridge_admit(%s,%s,%s,%s,%s)",
    "ack":"SELECT penny_bridge_ack(%s,%s,%s) AS recorded",
    "pending":"SELECT * FROM penny_bridge_pending_reply(%s)",
    "delivered":"SELECT penny_bridge_record_delivery(%s,%s,%s) AS recorded",
}


def reply_call(dsn,operation,args):
    try:
        if operation not in CALLS:
            raise ValueError("unknown reply operation")
        with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=5) as conn:
            conn.execute("SET LOCAL lock_timeout='5s'")
            conn.execute("SET LOCAL statement_timeout='10s'")
            rows=conn.execute(CALLS[operation],args).fetchall()
            if len(rows)>1:
                raise RuntimeError("unexpected mailbox reply rows")
            return rows[0] if rows else None
    except Exception as exc:
        logger.error("Mailbox delivery database call refused (%s)",type(exc).__name__)
        raise
