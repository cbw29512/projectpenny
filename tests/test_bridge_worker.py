"""One-cycle bridge recovery with real local DB and fake remote transport."""
from datetime import datetime,timedelta,timezone
from unittest.mock import Mock,patch
import unittest
from uuid import uuid4

import psycopg

from database_fixture import DSN,DatabaseFixture
from penny.bridge.state import RemoteClaim,BridgeResult
from penny.bridge.worker import run_bridge_once
from penny.bridge.release import approve_reply
from penny.scheduler.outcomes import complete


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class BridgeWorkerTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.owner,self.member,self.reviewer=uuid4(),uuid4(),uuid4()
        self.remote=RemoteClaim(uuid4(),self.owner,uuid4(),
            datetime.now(timezone.utc)+timedelta(minutes=10),"Question")
        self.client=Mock()
        self.client.claim.return_value=BridgeResult("claimed",self.remote)
        self.client.ack.return_value=BridgeResult("ok")
        self.client.answer.return_value=BridgeResult("ok")
        self.client.reject.return_value=BridgeResult("ok")
        with psycopg.connect(self.dsn) as conn:
            conn.execute("INSERT INTO bridge_member VALUES (%s,%s,true)",(self.owner,self.member))

    def enable(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE bridge_control SET enabled=true")

    def tick(self):
        return run_bridge_once(self.dsn,self.client).status

    def advance(self):
        # Synthetic operator-only time advancement; never reset in production.
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE bridge_control SET not_before=0")
        return self.tick()

    def finish(self,success=True):
        task=self.store.claim()
        self.assertIsNotNone(task)
        self.assertTrue(complete(self.dsn,task.task_id,task.fence,success=success,result="Draft"))

    def test_default_closed_and_persistent_cooldown(self):
        self.assertEqual(self.tick(),"paused")
        self.client.claim.assert_not_called()
        self.enable()
        self.assertEqual(self.tick(),"admitted")
        self.assertEqual(self.tick(),"cooldown")
        self.client.claim.assert_called_once()
        self.client.ack.assert_not_called()

    def test_end_to_end_with_review_and_delivery(self):
        self.enable()
        self.assertEqual(self.tick(),"admitted")
        self.assertEqual(self.advance(),"acknowledged")
        self.finish()
        self.assertEqual(self.advance(),"waiting_review")
        self.client.answer.assert_not_called()
        self.assertTrue(approve_reply(self.dsn,self.remote.id,reviewer_id=self.reviewer,expected_text="Draft"))
        self.assertEqual(self.advance(),"delivered")
        self.client.answer.assert_called_once_with(self.remote.id,self.remote.fence,"Draft")
        self.client.claim.return_value=BridgeResult("empty")
        self.assertEqual(self.advance(),"empty")

    def test_lost_ack_and_answer_are_retried_without_new_task(self):
        self.enable()
        self.assertEqual(self.tick(),"admitted")
        self.client.ack.side_effect=[BridgeResult("uncertain"),BridgeResult("ok")]
        self.assertEqual(self.advance(),"uncertain")
        self.assertEqual(self.advance(),"acknowledged")
        self.finish()
        self.assertTrue(approve_reply(self.dsn,self.remote.id,reviewer_id=self.reviewer,expected_text="Draft"))
        self.client.answer.side_effect=[BridgeResult("uncertain"),BridgeResult("ok")]
        self.assertEqual(self.advance(),"uncertain")
        self.assertEqual(self.advance(),"delivered")
        self.assertEqual(self.client.answer.call_args_list[0],self.client.answer.call_args_list[1])
        self.client.claim.assert_called_once()
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0],1)

    def test_backoff_and_authentication_stop(self):
        self.enable()
        self.client.claim.return_value=BridgeResult("backoff",retry_after=3600)
        self.assertEqual(self.tick(),"backoff")
        self.assertEqual(self.tick(),"cooldown")
        self.client.claim.return_value=BridgeResult("unauthorized")
        self.assertEqual(self.advance(),"blocked")
        self.assertEqual(self.advance(),"paused")

    def test_failed_task_rejected_once(self):
        self.enable()
        self.assertEqual(self.tick(),"admitted")
        self.assertEqual(self.advance(),"acknowledged")
        self.finish(success=False)
        self.assertEqual(self.advance(),"rejected")
        self.client.reject.assert_called_once_with(self.remote.id,self.remote.fence)
        self.client.claim.return_value=BridgeResult("empty")
        self.assertEqual(self.advance(),"empty")

    def test_identity_drift_and_busy_lock_no_network(self):
        self.enable()
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertEqual(self.tick(),"paused")
        from penny.bridge.worker_store import exclusive_cycle
        with exclusive_cycle(self.dsn) as acquired:
            self.assertTrue(acquired)
            self.assertEqual(self.tick(),"busy")
        self.client.claim.assert_not_called()
