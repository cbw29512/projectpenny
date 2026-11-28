"""Test-only subprocess adapter: fixed SQL, disposable DB, no network API."""
import json
import os
import re
import sys

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

OPERATIONS={
    "allow_write":("projection_writer","SELECT workshop_allow_write() AS ok",0),
    "allow_read":("projection_reader","SELECT workshop_allow_read() AS ok",0),
    "publish":("projection_writer","SELECT workshop_publish(%s,%s,%s,%s) AS ok",4),
    "read":("projection_reader","SELECT * FROM workshop_read()",0),
}


def main():
    try:
        value=json.load(sys.stdin)
        scope,query,count=OPERATIONS[value["operation"]]
        suffix=os.environ["PENNY_REHEARSAL_SUFFIX"]
        if not re.fullmatch(r"[a-f0-9]{32}",suffix) or len(value["args"])!=count:
            raise ValueError("invalid fixture")
        schema="mailbox_"+suffix
        with psycopg.connect(os.environ["PENNY_TEST_DSN"],row_factory=dict_row) as conn:
            if conn.info.dbname!="penny_test":
                raise PermissionError("disposable DB required")
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(scope+"_"+suffix)))
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            rows=conn.execute(query,value["args"]).fetchall()
        print(json.dumps(rows))
        return 0
    except Exception as exc:
        print("Disposable SQL adapter failed: "+type(exc).__name__,file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
