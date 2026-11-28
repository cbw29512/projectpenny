"""Synthetic activity candidate never exports content or member identifiers."""
import unittest
from unittest.mock import patch
from uuid import uuid4
from database_fixture import DSN, DatabaseFixture
from penny.progress.activity import browser_candidate
from penny.scheduler.storage_db import locked


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ActivityTests(DatabaseFixture):
    def test_safe_projection_and_blocked_status(self):
        self.assertEqual(browser_candidate(self.dsn)["state"],"paused")
        with locked(self.dsn) as (conn,_,now):
            conn.execute("UPDATE inference_runtime SET enabled=true")
        self.assertEqual(browser_candidate(self.dsn)["state"],"idle")
        self.store.submit(uuid4(),"private-key","private visitor message")
        self.assertIsNotNone(self.store.claim())
        state=browser_candidate(self.dsn)
        self.assertEqual(state["state"],"working")
        self.assertEqual(set(state),{"schema","status","state","sampled_at","expires_at"})
        self.assertNotIn("private",str(state))
        with locked(self.dsn) as (conn,_,now):
            conn.execute("UPDATE work_task SET lease_until=%s WHERE state='running'",(now,))
        self.assertEqual(browser_candidate(self.dsn)["state"],"blocked")
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertEqual(browser_candidate(self.dsn)["status"],"unavailable")
