"""Trusted operator state transitions; never manipulate actual services."""
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN,DatabaseFixture
from penny.runtime.operator_control import stop,start,recover_inference,clear_bridge_block
from penny.runtime.operator_status import status
from penny.bridge.worker_store import exclusive_cycle


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class OperatorTests(DatabaseFixture):
    def test_start_requires_confirmation_and_inference_before_bridge(self):
        self.assertFalse(start(self.dsn,"inference"))
        self.assertFalse(start(self.dsn,"bridge",confirmed=True))
        self.assertTrue(start(self.dsn,"inference",confirmed=True))
        self.assertTrue(start(self.dsn,"bridge",confirmed=True))
        s=status(self.dsn)
        self.assertTrue(s["bridge_enabled"])
        self.assertTrue(s["inference_enabled"])
        self.assertFalse(s["scheduler_paused"])

    def test_stop_works_during_identity_drift(self):
        self.assertTrue(start(self.dsn,"inference",confirmed=True))
        self.assertTrue(start(self.dsn,"bridge",confirmed=True))
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertTrue(stop(self.dsn))
            self.assertFalse(start(self.dsn,"inference",confirmed=True))
        s=status(self.dsn)
        self.assertTrue(s["scheduler_paused"])
        self.assertFalse(s["inference_enabled"])
        self.assertFalse(s["bridge_enabled"])

    def test_sticky_inference_recovery_requires_stopped_gates_and_attestation(self):
        self.assertTrue(start(self.dsn,"inference",confirmed=True))
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET uncertain=true")
        self.assertFalse(recover_inference(self.dsn,isolated=True))
        stop(self.dsn)
        self.assertFalse(recover_inference(self.dsn))
        self.assertFalse(start(self.dsn,"inference",confirmed=True))
        self.assertTrue(recover_inference(self.dsn,isolated=True))
        self.assertFalse(status(self.dsn)["inference_enabled"])
        self.assertTrue(status(self.dsn)["scheduler_paused"])

    def test_fenced_expired_recovery_never_steals_live_task(self):
        self.store.submit(None,"work","Private work")
        task=self.store.claim()
        self.assertIsNotNone(task)
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET uncertain=true")
        stop(self.dsn)
        self.assertFalse(recover_inference(self.dsn,isolated=True))
        self.assertFalse(recover_inference(self.dsn,isolated=True,
                         task_id=task.task_id,fence=task.fence))
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE work_task SET lease_until=0 WHERE id=%s",(task.task_id,))
        self.assertFalse(recover_inference(self.dsn,isolated=True,
                         task_id=task.task_id,fence=uuid4()))
        self.assertTrue(recover_inference(self.dsn,isolated=True,
                         task_id=task.task_id,fence=task.fence))
        self.assertIsNone(status(self.dsn)["active"])
        self.assertEqual(status(self.dsn)["task_counts"]["failed"],1)

    def test_bridge_block_requires_review_preserves_cooldown(self):
        stop(self.dsn)
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE bridge_control SET blocked_reason='authentication',not_before=9999999999")
        self.assertFalse(clear_bridge_block(self.dsn))
        self.assertTrue(clear_bridge_block(self.dsn,reviewed=True))
        s=status(self.dsn)
        self.assertIsNone(s["bridge_block"])
        self.assertFalse(s["bridge_enabled"])
        self.assertGreater(s["bridge_cooldown_seconds"],100)

    def test_busy_bridge_prevents_operator_enable(self):
        self.assertTrue(start(self.dsn,"inference",confirmed=True))
        with exclusive_cycle(self.dsn) as acquired:
            self.assertTrue(acquired)
            self.assertFalse(start(self.dsn,"bridge",confirmed=True))

    def test_audit_and_status_do_not_expose_payload(self):
        self.store.submit(None,"work","PRIVATE SECRET QUESTION")
        stop(self.dsn)
        self.assertNotIn("PRIVATE SECRET QUESTION",str(status(self.dsn)))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT action FROM runtime_operator_event").fetchall(),[("stop",)])
