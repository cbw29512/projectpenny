"""Private zero-cash business lifecycle on disposable PostgreSQL."""
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN,DatabaseFixture
from penny.business.state import Category,Metric,Action
from penny.business.store import stage,status
from penny.business.review import advance
from penny.vault.summary import summarize


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ExperimentTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        self.evidence=b"synthetic proposal"
        self.expiry=int(time.time())+3600

    def draft(self,ref="idea:1",**kw):
        args=dict(source_ref=ref,category=Category.DIGITAL_PRODUCT,title="Private template",
                  hypothesis="Five prototype checks pass",metric=Metric.PROTOTYPE_CHECKS_PASSED,
                  target=5,duration_seconds=600,additional_cash_cents=0,
                  evidence_ref=ref,evidence=self.evidence,reviewer_id=self.reviewer,
                  review_until=self.expiry)
        return stage(self.dsn,**(args|kw))

    def step(self,q,action,**kw):
        args=dict(action=action,expected_proposal_sha256=sha256(self.evidence).hexdigest(),
                  evidence_ref="review:synthetic",evidence=b"synthetic review",
                  reviewer_id=self.reviewer,confirmed=True)
        return advance(self.dsn,q,**(args|kw))

    def test_lifecycle_measured_failure_is_not_revenue(self):
        q=self.draft().entry_id
        self.assertEqual(status(self.dsn,q)["status"],"proposed")
        self.assertFalse(self.step(q,Action.START))
        self.assertTrue(self.step(q,Action.APPROVE))
        self.assertTrue(self.step(q,Action.START))
        self.assertTrue(self.step(q,Action.MEASURE,observed_at=int(time.time()),measured_count=3))
        result=status(self.dsn,q)
        self.assertEqual(result["status"],"measured")
        self.assertFalse(result["target_met"])
        self.assertEqual(result["authorized_cents"],0)
        self.assertEqual(summarize(self.dsn)["entry_count"],0)
        self.assertFalse(self.step(q,Action.MEASURE,observed_at=int(time.time()),measured_count=5))

    def test_one_active_and_explicit_stop(self):
        qs=[self.draft("idea:"+str(i)).entry_id for i in range(3)]
        for q in qs:
            self.assertTrue(self.step(q,Action.APPROVE))
        with ThreadPoolExecutor(max_workers=3) as pool:
            outcomes=list(pool.map(lambda q:self.step(q,Action.START),qs))
        self.assertEqual(sum(outcomes),1)
        active=qs[outcomes.index(True)]
        self.assertTrue(self.step(active,Action.STOP))
        self.assertFalse(self.step(active,Action.START))
        self.assertTrue(self.step(qs[outcomes.index(False)],Action.START))

    def test_replay_conflict_and_rejected(self):
        q=self.draft().entry_id
        self.assertTrue(self.draft().replayed)
        with self.assertRaises(ValueError):
            self.draft(target=6)
        self.assertTrue(self.step(q,Action.REJECT))
        self.assertFalse(self.step(q,Action.APPROVE))

    def test_zero_cash_and_identity_boundary(self):
        for kw in ({"additional_cash_cents":1},{"target":True},{"duration_seconds":999999},
                   {"title":" "},{"metric":"sales"},{"evidence":b""}):
            with self.assertRaises(ValueError):
                self.draft(**kw)
        q=self.draft().entry_id
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(self.draft("drift"))
            self.assertFalse(self.step(q,Action.APPROVE))
        self.assertFalse(self.step(q,Action.APPROVE,expected_proposal_sha256="bad"))

    def test_measurement_time_and_pause(self):
        q=self.draft().entry_id
        self.assertTrue(self.step(q,Action.APPROVE))
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE scheduler_control SET paused=true")
        self.assertFalse(self.step(q,Action.START))
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE scheduler_control SET paused=false")
        self.assertTrue(self.step(q,Action.START))
        for t in (1,int(time.time())+99999):
            self.assertFalse(self.step(q,Action.MEASURE,observed_at=t,measured_count=5))
        self.assertTrue(self.step(q,Action.MEASURE,observed_at=int(time.time()),measured_count=5))
        self.assertTrue(status(self.dsn,q)["target_met"])

    def test_immutable_history(self):
        q=self.draft().entry_id
        self.assertTrue(self.step(q,Action.APPROVE))
        for statement in ("DELETE FROM business_opportunity",
                          "UPDATE business_experiment_event SET action='rejected'"):
            with psycopg.connect(self.dsn) as conn:
                with self.assertRaises(psycopg.errors.RaiseException):
                    conn.execute(statement)
                conn.rollback()
