"""Disposable DB only: rest gates are independent of emergency controls."""
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from database_fixture import DSN, DatabaseFixture
from penny.progress.rest import configure, browser_candidate
from penny.progress.rest_schedule import RestWindow
from penny.runtime.inference import inference_tick
from penny.scheduler.storage_db import locked
from penny.scheduler.outcomes import complete
from penny.business.hourly import plan_hour


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class RestGateTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.window = RestWindow("2026-11-27", True, 4_000_000_000)

    def gate(self, resting):
        return patch("penny.scheduler.rest_gate.window_at",return_value=
                     RestWindow("2026-11-27",resting,4_000_000_000))

    def enable(self):
        self.assertTrue(configure(self.dsn,True,confirmed=True))
        with locked(self.dsn) as (conn,_,now):
            conn.execute("UPDATE inference_runtime SET enabled=true")
            conn.execute("UPDATE bridge_control SET enabled=true")

    def test_disabled_default_and_confirmed_persistence(self):
        self.assertFalse(configure(self.dsn,True))
        with self.gate(True):
            self.assertEqual(self.store.submit(None,"before","Work").status,"accept")
            self.enable()
            self.assertEqual(self.store.submit(None,"after","Work").status,"resting")
            self.assertIsNone(self.store.claim())
            self.assertTrue(self.store.submit(None,"before","Work").replayed)
            self.assertEqual(plan_hour(self.dsn,reviewer_id=uuid4(),confirmed=True)["outcome"],"paused")
            brain=Mock()
            # Supervised inference uses the database clock, not this Python mock.
            # Mailbox rest now uses its own database clock, not this Python mock.
            # Deterministic SQL boundary tests live in test_mailbox_role.py.
        with self.gate(False):
            self.assertIsNotNone(self.store.claim())

    def test_existing_fence_drains_and_wake_preserves_manual_pause(self):
        self.enable()
        with self.gate(False):
            self.store.submit(None,"work","Work")
            claim=self.store.claim()
        with self.gate(True):
            self.assertIsNone(self.store.claim())
            self.assertTrue(complete(self.dsn,claim.task_id,claim.fence,success=True,result="Draft"))
        self.store.set_paused(True)
        with self.gate(False):
            self.assertIsNone(self.store.claim())
            self.assertEqual(self.store.submit(None,"new","Work").status,"paused")
        self.assertTrue(configure(self.dsn,False,confirmed=True))
        with locked(self.dsn) as (conn,control,now):
            self.assertTrue(control["paused"])
            self.assertFalse(control["rest_enabled"])
            self.assertEqual(conn.execute("SELECT count(*) AS n FROM rest_policy_review").fetchone()["n"],2)

    def test_snapshot_never_calls_uncertainty_sleep(self):
        self.enable()
        with self.gate(True),patch("penny.progress.rest.window_at",return_value=self.window):
            self.assertEqual(browser_candidate(self.dsn)["state"],"asleep")
            with locked(self.dsn) as (conn,_,now):
                conn.execute("UPDATE inference_runtime SET uncertain=true")
            self.assertEqual(browser_candidate(self.dsn)["state"],"blocked")
            self.assertIsNone(browser_candidate(self.dsn)["wake_at"])
        # The SQL runtime gate preserves uncertainty independent of the Python clock mock.
        with locked(self.dsn) as (conn,_,now):
            self.assertTrue(conn.execute("SELECT uncertain FROM inference_runtime WHERE singleton").fetchone()["uncertain"])

    def test_invalid_clock_fails_closed(self):
        self.enable()
        with patch("penny.scheduler.rest_gate.window_at",return_value=None):
            self.assertEqual(self.store.submit(None,"clock","Work").status,"resting")
            self.assertIsNone(self.store.claim())
