"""Single migration-complete fixture for every disposable PostgreSQL suite."""
import os
import unittest
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from penny.scheduler.storage import TaskStore

DSN = os.environ.get("PENNY_TEST_DSN")


def migration_paths():
    # All suites exercise the current schema, including future migrations.
    paths = sorted(Path("migrations").glob("*.sql"))
    if not paths:
        raise RuntimeError("migration directory missing")
    return paths


class DatabaseFixture(unittest.TestCase):
    def setUp(self):
        self.schema = "penny_test_" + uuid4().hex
        with psycopg.connect(DSN,autocommit=True) as conn:
            if conn.info.dbname != "penny_test":
                raise RuntimeError("expected disposable penny_test database")
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.addCleanup(self.drop_schema)
        self.dsn = make_conninfo(DSN,options="-c search_path="+self.schema)
        with psycopg.connect(self.dsn,autocommit=True) as conn:
            for path in migration_paths():
                conn.execute(path.read_text())
        self.store = TaskStore(self.dsn)

    def drop_schema(self):
        with psycopg.connect(DSN,autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
