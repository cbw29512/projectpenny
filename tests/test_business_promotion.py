"""Actual PostgreSQL promotion transaction with synthetic model/evidence."""
import json
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from unittest.mock import Mock,patch
from uuid import uuid4

import psycopg
from database_fixture import DSN,DatabaseFixture
from penny.business.draft_admission import submit_draft
from penny.business.draft_intake import draft_status
from penny.business.promote import promote
from penny.business.store import stage,status
from penny.business.state import Category,Metric,Action
from penny.business.review import advance
from penny.scheduler.worker import run_once,WorkerResult

RAW=json.dumps(dict(category="digital_product",title="Private checklist",
    hypothesis="Five checks pass",metric="prototype_checks_passed",target=5,
    duration_seconds=600,additional_cash_cents=0))


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class PromotionTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        self.until=int(time.time())+3600
        self.task=submit_draft(self.dsn,key="one",brief="Checklist",
                               reviewer_id=self.reviewer).task_id

    def finish(self,raw=RAW):
        brain=Mock()
        brain.generate.return_value=raw
        self.assertEqual(run_once(self.store,brain),WorkerResult.COMPLETED)

    def promote(self,**kw):
        args=dict(expected_result_sha256=sha256(RAW.encode()).hexdigest(),
                  evidence_ref="private:market-review",evidence=b"synthetic independent review",
                  reviewer_id=self.reviewer,review_until=self.until,confirmed=True)
        return promote(self.dsn,self.task,**(args|kw))

    def test_reviewed_promotion_is_not_experiment_approval(self):
        self.finish()
        receipt=self.promote()
        self.assertEqual(status(self.dsn,receipt.entry_id)["status"],"proposed")
        result=draft_status(self.dsn,self.task)
        self.assertEqual(result["status"],"promoted")
        self.assertEqual(result["opportunity_id"],receipt.entry_id)
        self.assertEqual(result["authorized_cents"],0)
        args=dict(expected_proposal_sha256=sha256(b"synthetic independent review").hexdigest(),
                  evidence_ref="private:decision",evidence=b"synthetic decision",
                  reviewer_id=self.reviewer,confirmed=True)
        self.assertFalse(advance(self.dsn,receipt.entry_id,action=Action.START,**args))
        self.assertTrue(advance(self.dsn,receipt.entry_id,action=Action.APPROVE,**args))
        self.assertTrue(advance(self.dsn,receipt.entry_id,action=Action.START,**args))

    def test_concurrent_exact_replay_and_conflict(self):
        self.finish()
        with ThreadPoolExecutor(max_workers=3) as pool:
            rows=list(pool.map(lambda _:self.promote(),range(3)))
        self.assertEqual(len({r.entry_id for r in rows}),1)
        self.assertEqual(sum(not r.replayed for r in rows),1)
        with self.assertRaises(ValueError):
            self.promote(evidence=b"changed review")

    def test_requires_fenced_candidate_and_exact_digest(self):
        self.assertIsNone(self.promote())
        self.finish()
        self.assertIsNone(self.promote(expected_result_sha256="0"*64))
        with self.assertRaises(ValueError):
            self.promote(confirmed=False)
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(self.promote())

    def test_raw_result_drift_refused(self):
        self.finish()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE task_outcome SET result='altered' WHERE task_id=%s",(self.task,))
        self.assertIsNone(self.promote())

    def test_reserved_source_cannot_be_manually_staged(self):
        with self.assertRaises(ValueError):
            stage(self.dsn,source_ref="draft:"+str(self.task),category=Category.CONTENT,
                  title="Forged",hypothesis="Forged",metric=Metric.QUALIFIED_INTEREST,
                  target=1,duration_seconds=600,additional_cash_cents=0,
                  evidence_ref="private:fake",evidence=b"fake",reviewer_id=self.reviewer,
                  review_until=self.until)

    def test_invalid_draft_not_promoted(self):
        self.finish("not structured")
        self.assertIsNone(self.promote())
