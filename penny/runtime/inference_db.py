"""Fixed inference supervisor calls; no direct runtime-gate table writes."""
import logging
import psycopg
from psycopg.rows import dict_row

logger=logging.getLogger(__name__)
CALLS={
    "begin":"SELECT * FROM penny_inference_begin()",
    "finish":"SELECT penny_inference_finish(%s,%s) AS status",
}


def gate_call(dsn,operation,args=()):
    try:
        if operation not in CALLS:
            raise ValueError("unknown inference gate operation")
        with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=5) as conn:
            conn.execute("SET LOCAL lock_timeout='5s'")
            conn.execute("SET LOCAL statement_timeout='10s'")
            rows=conn.execute(CALLS[operation],args).fetchall()
            if len(rows)!=1:
                raise RuntimeError("unexpected inference gate rows")
            return rows[0]
    except Exception as exc:
        logger.error("Inference gate call refused (%s)",type(exc).__name__)
        raise
