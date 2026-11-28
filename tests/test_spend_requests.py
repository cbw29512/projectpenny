import time
import unittest
from uuid import uuid4
from unittest.mock import patch

from database_fixture import DSN, DatabaseFixture
from penny.vault.spend_requests import stage, reject, status
from penny.vault.spend_state import Purpose, Rejection
from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class SpendRequestTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        self.expiry=int(time.time())+3600

    def draft(self,**kw):
        args=dict(source_ref="quote:1",purpose=Purpose.COMPUTE,cents=100,
                  quote_ref="private:quote",evidence=b"synthetic quote",
                  reviewer_id=self.reviewer,expires_at=self.expiry)
        return stage(self.dsn,**(args|kw))

    def test_pending_never_authorizes_money(self):
        receipt=self.draft()
        self.assertEqual(status(self.dsn,receipt.entry_id),
            {"status":"pending","requested_cents":100,"reason":None,
             "authorized_cents":0,"reserved_cents":0})
        for actor in Actor:
            self.assertFalse(authorize(actor,Capability.SPEND).allowed)

    def test_replay_and_conflict(self):
        first=self.draft()
        second=self.draft()
        self.assertEqual(first.entry_id,second.entry_id)
        self.assertTrue(second.replayed)
        with self.assertRaises(ValueError):
            self.draft(cents=101)

    def test_rejection_is_terminal(self):
        receipt=self.draft()
        self.assertTrue(reject(self.dsn,receipt.entry_id,reviewer_id=self.reviewer,reason=Rejection.COST))
        self.assertFalse(reject(self.dsn,receipt.entry_id,reviewer_id=self.reviewer,reason=Rejection.RISK))
        self.assertEqual(status(self.dsn,receipt.entry_id)["reason"],"cost")
        self.assertEqual(status(self.dsn,receipt.entry_id)["status"],"rejected")

    def test_invalid_and_identity_drift(self):
        for kw in ({"cents":True},{"cents":0},{"purpose":"compute"},
                   {"expires_at":1},{"evidence":b""}):
            with self.assertRaises(ValueError):
                self.draft(**kw)
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(self.draft())

    def test_unknown_request(self):
        key=uuid4()
        self.assertIsNone(status(self.dsn,key))
        self.assertFalse(reject(self.dsn,key,reviewer_id=self.reviewer,reason=Rejection.COST))
