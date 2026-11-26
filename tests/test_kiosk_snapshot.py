"""Kiosk projection excludes member content and raw internal drafts."""
import unittest
from uuid import uuid4

import psycopg

from database_fixture import DSN, DatabaseFixture


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class KioskSnapshotTests(DatabaseFixture):
    def read(self):
        with psycopg.connect(self.dsn) as conn:
            return conn.execute("SELECT snapshot FROM kiosk_snapshot").fetchone()[0]

    def test_initial_state(self):
        s = self.read()
        self.assertFalse(s["enabled"])
        self.assertIsNone(s["active"])
        self.assertEqual(s["recent"], [])
        self.assertFalse(s["visitor_busy"])

    def test_member_payload_and_raw_result_never_projected(self):
        with psycopg.connect(self.dsn) as conn:
            task = uuid4()
            conn.execute("""INSERT INTO work_task
                (id,member_id,tier_snapshot,idempotency_key,payload,submitted_at,deadline,state)
                VALUES (%s,%s,0,'visitor','PRIVATE_VISITOR_TEXT',1,9999999999,'succeeded')""",
                (task,uuid4()))
            conn.execute("INSERT INTO task_outcome VALUES (%s,'succeeded','PRIVATE_VISITOR_RESULT',2,1)", (task,))
            internal = uuid4()
            conn.execute("""INSERT INTO work_task
                (id,idempotency_key,payload,submitted_at,deadline,state)
                VALUES (%s,'internal','PRIVATE_PROMPT',1,9999999999,'succeeded')""", (internal,))
            conn.execute("INSERT INTO task_outcome VALUES (%s,'succeeded','RAW_INTERNAL_RESULT',2,1)", (internal,))
        s = self.read()
        self.assertEqual(s["counts"], {"succeeded":1})
        self.assertEqual(s["recent"], [])
        for secret in ("PRIVATE_VISITOR_TEXT","PRIVATE_VISITOR_RESULT","PRIVATE_PROMPT","RAW_INTERNAL_RESULT"):
            self.assertNotIn(secret,str(s))

    def test_running_internal_task_only_safe_metadata(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute("""INSERT INTO work_task
                (id,idempotency_key,payload,submitted_at,deadline,state,fence,started_at,lease_until)
                VALUES (%s,'internal','PRIVATE_PROMPT',1,9999999999,'running',%s,2,9999999999)""",
                (uuid4(),uuid4()))
        s = self.read()
        self.assertEqual(s["active"]["kind"],"internal task")
        self.assertNotIn("PRIVATE_PROMPT",str(s))
        self.assertNotIn("fence",s["active"])
