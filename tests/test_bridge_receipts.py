"""Durable cloud-to-local mapping regression tests on disposable PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN, DatabaseFixture
from penny.bridge.receipts import admit_claim, record_ack
from penny.bridge.state import RemoteClaim
from penny.scheduler.outcomes import complete


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class BridgeReceiptTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.owner,self.member=uuid4(),uuid4()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("INSERT INTO bridge_member VALUES (%s,%s,true)",(self.owner,self.member))
        self.claim=RemoteClaim(uuid4(),self.owner,uuid4(),
            datetime.now(timezone.utc)+timedelta(minutes=5),"Question")

    def admit(self,claim=None):
        return admit_claim(self.dsn,claim or self.claim)

    def count(self):
        with psycopg.connect(self.dsn) as conn:
            return conn.execute("SELECT (SELECT count(*) FROM work_task),(SELECT count(*) FROM bridge_receipt)").fetchone()

    def test_concurrent_replay_is_exactly_one_local_task(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            receipts=list(pool.map(lambda _:self.admit(),range(8)))
        self.assertTrue(all(r.status=="accept" for r in receipts))
        self.assertEqual(len({r.task_id for r in receipts}),1)
        self.assertEqual(sum(not r.replayed for r in receipts),1)
        self.assertEqual(self.count(),(1,1))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT member_id FROM work_task").fetchone()[0],self.member)
            self.assertEqual(conn.execute("SELECT count(*) FROM member_recall_scope").fetchone()[0],0)

    def test_conflicting_payload_fence_and_owner_never_create_work(self):
        self.assertEqual(self.admit().status,"accept")
        for claim in (replace(self.claim,text="Different"),replace(self.claim,fence=uuid4()),
                      replace(self.claim,id=uuid4())):
            self.assertEqual(self.admit(claim).status,"conflict")
        self.assertEqual(self.admit(replace(self.claim,owner=uuid4())).status,"denied")
        self.assertEqual(self.count(),(1,1))

    def test_expiry_and_identity_fail_closed(self):
        for lease in (datetime.now(timezone.utc)-timedelta(seconds=1),
                      datetime.now(timezone.utc)+timedelta(hours=1)):
            self.assertEqual(self.admit(replace(self.claim,lease_until=lease)).status,"expired")
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertEqual(self.admit().status,"identity_unavailable")
        self.assertEqual(self.count(),(0,0))

    def test_existing_scheduler_limits_and_reserved_namespace(self):
        self.assertEqual(self.store.submit(self.member,"bridge:"+str(self.claim.id),"Question").status,"invalid")
        self.store.set_paused(True)
        self.assertEqual(self.admit().status,"paused")
        self.store.set_paused(False)
        self.assertEqual(self.admit().status,"accept")
        self.assertEqual(self.count(),(1,1))

    def test_ack_is_fenced_idempotent_and_revocable(self):
        receipt=self.admit()
        self.assertFalse(record_ack(self.dsn,self.claim.id,uuid4(),receipt.task_id))
        self.assertFalse(record_ack(self.dsn,self.claim.id,self.claim.fence,uuid4()))
        for _ in range(2):
            self.assertTrue(record_ack(self.dsn,self.claim.id,self.claim.fence,receipt.task_id))
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE bridge_member SET enabled=false WHERE cloud_owner=%s",(self.owner,))
        self.assertFalse(record_ack(self.dsn,self.claim.id,self.claim.fence,receipt.task_id))
        self.assertEqual(self.admit().status,"denied")

    def test_receipt_failure_rolls_back_task(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute("""CREATE FUNCTION reject_bridge_receipt() RETURNS trigger
                LANGUAGE plpgsql AS $test_body$ BEGIN RAISE EXCEPTION 'test rollback'; END; $test_body$""")
            conn.execute("""CREATE TRIGGER reject_receipt BEFORE INSERT ON bridge_receipt
                FOR EACH ROW EXECUTE FUNCTION reject_bridge_receipt()""")
        with self.assertRaises(psycopg.Error):
            self.admit()
        self.assertEqual(self.count(),(0,0))

    def test_deadline_bounded_and_quota_shared(self):
        for i in range(3):
            receipt=self.admit(replace(self.claim,id=uuid4(),fence=uuid4()))
            self.assertEqual(receipt.status,"accept")
            task=self.store.claim()
            self.assertIsNotNone(task)
            self.assertLessEqual(task.lease_until,int(self.claim.lease_until.timestamp())-5)
            self.assertTrue(complete(self.dsn,task.task_id,task.fence,success=True,result="draft"))
        self.assertEqual(self.admit().status,"member_quota")
        self.assertEqual(self.count(),(3,3))
