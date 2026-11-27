"""Mailbox delivery calls; no raw draft or approval table access."""
import logging

import psycopg
from psycopg.rows import dict_row

logger=logging.getLogger(__name__)
CALLS={
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
