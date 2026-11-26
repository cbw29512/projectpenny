"""Synthetic Workshop output and human review evidence in disposable PostgreSQL."""
import time
import unittest
from hashlib import sha256
from unittest.mock import Mock,patch
from uuid import uuid4

import psycopg
from database_fixture import DSN,DatabaseFixture
from test_workshop import RAW
from penny.business.store import stage
from penny.business.state import Category,Metric,Action
from penny.business.review import advance
from penny.business.workshop_admission import submit_prototype
from penny.business.workshop_intake import read_artifact
from penny.business.quality import review,quality_status,export_private
from penny.business.quality_state import CRITERIA
from penny.scheduler.worker import run_once,WorkerResult


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class QualityTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        evidence=b"synthetic opportunity"
        q=stage(self.dsn,source_ref="test-quality",category=Category.DIGITAL_PRODUCT,
                title="Checklist",hypothesis="Usable prototype",metric=Metric.PROTOTYPE_CHECKS_PASSED,
                target=3,duration_seconds=600,additional_cash_cents=0,evidence_ref="test:evidence",
                evidence=evidence,reviewer_id=self.reviewer,review_until=int(time.time())+3600).entry_id
        for action in (Action.APPROVE,Action.START):
            self.assertTrue(advance(self.dsn,q,action=action,
                expected_proposal_sha256=sha256(evidence).hexdigest(),
                evidence_ref="test:review",evidence=b"synthetic decision",
                reviewer_id=self.reviewer,confirmed=True))
        self.task=submit_prototype(self.dsn,q,key="quality",reviewer_id=self.reviewer).task_id
        brain=Mock()
        brain.generate.return_value=RAW
        self.assertEqual(run_once(self.store,brain),WorkerResult.COMPLETED)
        self.artifact=read_artifact(self.dsn,self.task)["artifact"]
        self.digest=self.artifact["content_sha256"]

    def review(self,ref="quality:one",**kw):
        args=dict(source_ref=ref,expected_content_sha256=self.digest,
                  checks={k:True for k in CRITERIA},revoked=False,
                  reviewer_id=self.reviewer,evidence_ref="private:quality",
                  evidence=b"synthetic human review",confirmed=True)
        return review(self.dsn,self.task,**(args|kw))

    def export(self,key,**kw):
        args=dict(expected_review_id=key,expected_content_sha256=self.digest)
        return export_private(self.dsn,self.task,**(args|kw))

    def test_pass_required_and_exact_export_bytes(self):
        self.assertEqual(quality_status(self.dsn,self.task)["status"],"unreviewed")
        self.assertIsNone(self.export(uuid4()))
        receipt=self.review()
        self.assertTrue(self.review().replayed)
        product=self.export(receipt.entry_id)
        self.assertEqual(product.content,self.artifact["content"].encode())
        self.assertEqual(sha256(product.content).hexdigest(),self.digest)
        self.assertNotIn(self.artifact["content"],repr(product))
        self.assertFalse(quality_status(self.dsn,self.task)["commercial_release_authorized"])

    def test_failed_check_blocks_and_new_review_supersedes(self):
        checks={k:k!="accuracy" for k in CRITERIA}
        failed=self.review(checks=checks)
        self.assertEqual(quality_status(self.dsn,self.task)["status"],"failed")
        self.assertIsNone(self.export(failed.entry_id))
        passed=self.review("quality:two")
        self.assertIsNotNone(self.export(passed.entry_id))
        self.assertIsNone(self.export(failed.entry_id))

    def test_revocation_terminal_and_replay_not_reactivation(self):
        passed=self.review()
        self.review("quality:revoke",checks={k:False for k in CRITERIA},revoked=True)
        self.assertEqual(quality_status(self.dsn,self.task)["status"],"revoked")
        self.assertTrue(self.review().replayed)
        self.assertIsNone(self.review("quality:again"))
        self.assertIsNone(self.export(passed.entry_id))

    def test_exact_digest_and_strict_rubric(self):
        self.assertIsNone(self.review(expected_content_sha256="0"*64))
        for kw in ({"checks":{}},{"checks":{k:1 for k in CRITERIA}},{"confirmed":False}):
            with self.assertRaises(ValueError):
                self.review(**kw)
        receipt=self.review()
        with self.assertRaises(ValueError):
            self.review(evidence=b"changed")
        self.assertIsNone(self.export(receipt.entry_id,expected_content_sha256="0"*64))

    def test_integrity_drift_and_revoke(self):
        receipt=self.review()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE task_outcome SET result='changed' WHERE task_id=%s",(self.task,))
        self.assertIsNone(self.export(receipt.entry_id))
        self.assertEqual(quality_status(self.dsn,self.task)["status"],"unavailable")
        self.assertIsNotNone(self.review("quality:revoke",checks={k:False for k in CRITERIA},revoked=True))

    def test_identity_drift_and_immutable_review(self):
        receipt=self.review()
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(self.export(receipt.entry_id))
            self.assertIsNone(self.review("quality:new"))
        with psycopg.connect(self.dsn) as conn:
            with self.assertRaises(psycopg.errors.RaiseException):
                conn.execute("DELETE FROM workshop_quality_review")
            conn.rollback()

    def test_operator_inspection_matches_current_review(self):
        from penny.business.workshop_operator import recent,inspect
        self.assertEqual(recent(self.dsn)[0]["task_id"],str(self.task))
        before=inspect(self.dsn,self.task)
        self.assertEqual(before["quality_status"],"unreviewed")
        receipt=self.review()
        after=inspect(self.dsn,self.task)
        self.assertEqual(after["review_id"],str(receipt.entry_id))
        self.assertEqual(after["reviewed_digest"],self.digest)
        self.assertTrue(after["private_export_ready"])
        self.assertFalse(after["commercial_release_authorized"])
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(recent(self.dsn))
            self.assertIsNone(inspect(self.dsn,self.task))
