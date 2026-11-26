"""The integration fixture must discover the entire ordered migration set."""
import unittest
from database_fixture import DSN, DatabaseFixture, migration_paths
import psycopg


class MigrationDiscoveryTests(unittest.TestCase):
    def test_contiguous_order(self):
        paths = migration_paths()
        self.assertEqual([int(p.name.split("_",1)[0]) for p in paths],
                         list(range(1,len(paths)+1)))


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class FullSchemaTests(DatabaseFixture):
    def test_current_scheduler_and_memory_tables_exist(self):
        with psycopg.connect(self.dsn) as conn:
            for table in ("work_task","task_outcome","memory_candidate",
                          "business_memory","member_session","member_recall_scope",
                          "member_recall_snapshot"):
                self.assertIsNotNone(conn.execute("SELECT to_regclass(%s)",(table,)).fetchone()[0])
