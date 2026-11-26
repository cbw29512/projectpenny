"""Approved answer boundary tests, using real disposable PostgreSQL."""
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN,DatabaseFixture
from penny.bridge.receipts import admit_claim,record_ack
from penny.bridge.release import approve_reply,pending_reply,record_delivery
from penny.bridge.state import RemoteClaim
from penny.scheduler.outcomes import complete


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class BridgeReleaseTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.owner,self.member,self.reviewer=uuid4(),uuid4(),uuid4()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("INSERT INTO bridge_member VALUES (%s,%s,true)",(self.owner,self.member))
        self.remote=RemoteClaim(uuid4(),self.owner,uuid4(),
            datetime.now(timezone.utc)+timedelta(minutes=5),"Question")
        self.receipt=admit_claim(self.dsn,self.remote)
        self.assertEqual(self.receipt.status,"accept")

    def ack(self):
        self.assertTrue(record_ack(self.dsn,self.remote.id,self.remote.fence,self.receipt.task_id))

    def finish(self,success=True):
        task=self.store.claim()
        self.assertTrue(complete(self.dsn,task.task_id,task.fence,success=success,result="Draft"))

    def approve(self,text="Draft"):
        return approve_reply(self.dsn,self.remote.id,reviewer_id=self.reviewer,expected_text=text)

    def pending(self):
        return pending_reply(self.dsn,self.remote.id)

    def test_requires_ack_completion_and_review(self):
        self.assertFalse(self.approve())
        self.finish()
        self.assertFalse(self.approve())
        self.ack()
        self.assertIsNone(self.pending())
        self.assertFalse(self.approve("Different"))
        self.assertTrue(self.approve())
        self.assertTrue(self.approve())
        self.assertEqual(self.pending().text,"Draft")

    def test_delivery_replay_and_forgery(self):
        self.ack()
        self.finish()
        self.assertTrue(self.approve())
        reply=self.pending()
        self.assertFalse(record_delivery(self.dsn,replace(reply,fence=uuid4())))
        self.assertFalse(record_delivery(self.dsn,replace(reply,text="changed")))
        self.assertTrue(record_delivery(self.dsn,reply))
        self.assertTrue(record_delivery(self.dsn,reply))
        self.assertIsNone(self.pending())

    def test_disabled_member_and_identity_drift_block_release(self):
        self.ack()
        self.finish()
        self.assertTrue(self.approve())
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(self.pending())
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE bridge_member SET enabled=false WHERE cloud_owner=%s",(self.owner,))
        self.assertIsNone(self.pending())

    def test_mutated_draft_invalidates_approval(self):
        self.ack()
        self.finish()
        self.assertTrue(self.approve())
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE task_outcome SET result='changed' WHERE task_id=%s",(self.receipt.task_id,))
        self.assertIsNone(self.pending())
        self.assertFalse(self.approve("changed"))

    def test_failed_work_cannot_be_approved(self):
        self.ack()
        self.finish(success=False)
        self.assertFalse(self.approve())
        self.assertIsNone(self.pending())

    def test_pause_blocks_publication_candidate(self):
        self.ack()
        self.finish()
        self.assertTrue(self.approve())
        self.store.set_paused(True)
        self.assertIsNone(self.pending())
        self.store.set_paused(False)
        self.assertIsNotNone(self.pending())
