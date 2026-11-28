"""Synthetic local community delivery; no remote calls."""
import time
import unittest
from uuid import uuid4
import psycopg
from database_fixture import DSN, DatabaseFixture
from penny.community.bridge import admit_community_claim
from penny.auth.session import issue_session
from penny.community.intake import submit_suggestion


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class CommunityBridgeTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.cloud, self.owner = uuid4(), uuid4()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("INSERT INTO bridge_member(cloud_owner,local_member) VALUES (%s,%s)",
                         (self.cloud,self.owner))
        now = int(time.time())
        self.args = dict(cloud_id=uuid4(),cloud_owner=self.cloud,key=uuid4(),
                         fence=uuid4(),body="A useful calendar",
                         expires_at=now+600,lease_until=now+300)

    def admit(self, **changes):
        return admit_community_claim(self.dsn, **(self.args | changes))

    def test_receipt_replay_conflict_and_mapping(self):
        first = self.admit()
        self.assertEqual(first.status,"accepted")
        self.assertEqual(self.admit().suggestion_id,first.suggestion_id)
        self.assertTrue(self.admit().replay)
        self.assertEqual(self.admit(body="Different idea").status,"idempotency_conflict")
        self.assertEqual(self.admit(cloud_owner=uuid4()).status,"denied")
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM community_bridge_receipt").fetchone()[0],1)
            self.assertEqual(conn.execute("SELECT count(*) FROM community_suggestion").fetchone()[0],1)
            self.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0],0)
            conn.execute("UPDATE bridge_member SET enabled=false WHERE cloud_owner=%s",(self.cloud,))
        self.assertEqual(self.admit().status,"denied")

    def test_local_quota_and_expiry(self):
        token = issue_session(self.dsn,self.owner).token
        for i in range(3):
            self.assertEqual(submit_suggestion(self.dsn,token,key=str(i),body="Idea "+str(i)).status,"accepted")
        self.assertEqual(self.admit().status,"member_limit")
        self.assertEqual(self.admit(lease_until=1).status,"denied")
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM community_bridge_receipt").fetchone()[0],0)

    def test_conflicting_fence_and_key_cannot_create_receipt(self):
        first = self.admit()
        self.assertEqual(first.status,"accepted")
        self.assertEqual(self.admit(cloud_id=uuid4()).status,"idempotency_conflict")
        self.assertEqual(self.admit(cloud_id=uuid4(),fence=uuid4()).status,"idempotency_conflict")
        self.assertEqual(self.admit(cloud_id=uuid4(),key=uuid4()).status,"idempotency_conflict")
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM community_bridge_receipt").fetchone()[0],1)

    def test_receipt_failure_rolls_back_suggestion(self):
        from unittest.mock import patch
        from contextlib import contextmanager
        from penny.scheduler.storage_db import locked

        @contextmanager
        def fail_receipt(dsn):
            with locked(dsn) as (conn,control,now):
                class Connection:
                    def execute(self,statement,*args):
                        if statement.startswith("INSERT INTO community_bridge_receipt"):
                            raise RuntimeError("synthetic receipt failure")
                        return conn.execute(statement,*args)
                yield Connection(),control,now

        with patch("penny.community.bridge.locked",fail_receipt):
            with self.assertRaises(RuntimeError):
                self.admit()
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM community_suggestion").fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT count(*) FROM community_bridge_receipt").fetchone()[0],0)
