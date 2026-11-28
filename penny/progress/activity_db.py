"""Fixed activity-only DB calls, no direct scheduler-table access."""
import logging

import psycopg
from psycopg.rows import dict_row

logger=logging.getLogger(__name__)
# Fixed SQL, no user-provided SQL or identifiers.
CALLS={
    "reserve":"SELECT penny_activity_reserve(%s) AS result",
    "finish":"SELECT penny_activity_finish(%s) AS result",
    "inputs":"SELECT * FROM penny_activity_inputs()",
}


def activity_call(dsn,operation,args=()):
    try:
        if operation not in CALLS:
            raise ValueError("unknown activity operation")
        with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=5) as conn:
            conn.execute("SET LOCAL lock_timeout='5s'")
            conn.execute("SET LOCAL statement_timeout='10s'")
            rows=conn.execute(CALLS[operation],args).fetchall()
            if len(rows)!=1:
                raise RuntimeError("activity routine returned unexpected rows")
            return rows[0]
    except Exception as exc:
        logger.error("Activity database call refused (%s)",type(exc).__name__)
        raise
