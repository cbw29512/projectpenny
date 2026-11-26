"""Beta preview review is separate from commercial quality; synthetic only."""
import time
import unittest
from hashlib import sha256
from unittest.mock import Mock,patch
from uuid import uuid4

from database_fixture import DSN,DatabaseFixture
from test_workshop import RAW
from penny.business.store import stage
from penny.business.state import Category,Metric,Action
from penny.business.review import advance
from penny.business.workshop_admission import submit_prototype
from penny.business.workshop_intake import read_artifact
from penny.business.preview import approve,read_preview,withdraw
from penny.business.quality import quality_status,review
from penny.business.quality_state import CRITERIA
from penny.scheduler.worker import run_once,WorkerResult


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class PreviewTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        evidence=b"synthetic proposal"
        self.q=stage(self.dsn,source_ref="preview:test",category=Category.DIGITAL_PRODUCT,
            title="Checklist",hypothesis="Usable checklist",metric=Metric.PROTOTYPE_CHECKS_PASSED,
            target=3,duration_seconds=600,additional_cash_cents=0,evidence_ref="test:proposal",
            evidence=evidence,reviewer_id=self.reviewer,review_until=int(time.time())+3600).entry_id
        for action in (Action.APPROVE,Action.START):
            self.assertTrue(advance(self.dsn,self.q,action=action,
                expected_proposal_sha256=sha256(evidence).hexdigest(),evidence_ref="test:decision",
                evidence=b"synthetic decision",reviewer_id=self.reviewer,confirmed=True))
        self.task=submit_prototype(self.dsn,self.q,key="beta",reviewer_id=self.reviewer).task_id
        brain=Mock()
        brain.generate.return_value=RAW
        self.assertEqual(run_once(self.store,brain),WorkerResult.COMPLETED)
        self.digest=read_artifact(self.dsn,self.task)["artifact"]["content_sha256"]
        self.args=dict(source_ref="preview:one",artifact_sha256=self.digest,title="Beta checklist",
            preview_text="Please evaluate this synthetic excerpt.",reviewer_id=self.reviewer,
            evidence_ref="test:preview",evidence=b"synthetic safety review",
            expires_at=int(time.time())+300,confirmed=True)

    def approve(self,**kwargs):
        return approve(self.dsn,self.task,**(self.args|kwargs))

    def test_beta_without_quality_pass_has_no_sale_authority(self):
        self.assertEqual(quality_status(self.dsn,self.task)["status"],"unreviewed")
        p=self.approve()
        self.assertTrue(self.approve().replayed)
        data=read_preview(self.dsn,p.entry_id)
        self.assertEqual(data["preview_text"],self.args["preview_text"])
        self.assertEqual(data["status"],"beta_feedback_only")
        self.assertFalse(data["commercial_release_authorized"])
        self.assertNotIn("task_id",data)
        self.assertNotIn("reviewer_id",data)
        self.assertNotIn("evidence_ref",data)
        self.assertIsNone(self.approve(source_ref="preview:duplicate"))

    def test_confirmation_integrity_and_expiry(self):
        with self.assertRaises(ValueError):
            self.approve(confirmed=False)
        self.assertIsNone(self.approve(artifact_sha256="a"*64))
        self.assertIsNone(self.approve(expires_at=int(time.time())-1))
        self.assertIsNone(self.approve(expires_at=int(time.time())+700000))
        with self.assertRaises(ValueError):
            self.approve(preview_text="hidden\u202e")
        p=self.approve()
        with self.assertRaises(ValueError):
            self.approve(title="Changed")
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(read_preview(self.dsn,p.entry_id))

    def test_withdrawal_replay_does_not_reactivate(self):
        p=self.approve()
        self.assertTrue(withdraw(self.dsn,p.entry_id,reviewer_id=self.reviewer,
            evidence_ref="test:withdraw",evidence=b"synthetic withdrawal",confirmed=True))
        self.assertIsNone(read_preview(self.dsn,p.entry_id))
        self.assertTrue(self.approve().replayed)
        self.assertIsNone(read_preview(self.dsn,p.entry_id))

    def test_revoked_quality_hides_preview(self):
        p=self.approve()
        for revoked in (False,True):
            self.assertIsNotNone(review(self.dsn,self.task,
                source_ref="quality:"+str(revoked),expected_content_sha256=self.digest,
                checks={k:not revoked for k in CRITERIA},revoked=revoked,
                reviewer_id=self.reviewer,evidence_ref="test:quality",
                evidence=b"synthetic quality",confirmed=True))
        self.assertIsNone(read_preview(self.dsn,p.entry_id))
        self.assertIsNone(self.approve(source_ref="preview:after-revoke"))
