"""Moderation, withdrawal and private aggregate regression tests."""
import unittest
from uuid import uuid4
from unittest.mock import patch

import psycopg
import test_showroom_feedback as fixture
from database_fixture import DSN,DatabaseFixture
from penny.auth.session import issue_session
from penny.business.preview import withdraw
from penny.community.feedback import own_feedback,withdraw_feedback
from penny.community.feedback_review import review_feedback
from penny.community.feedback_summary import feedback_summary
from penny.community.intake import submit_suggestion


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class FeedbackReviewTests(DatabaseFixture):
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
        self.preview=approve(self.dsn,self.task,**self.args).entry_id
        self.hash=read_preview(self.dsn,self.preview)["preview_sha256"]
        self.token=issue_session(self.dsn,uuid4()).token
        self.other=issue_session(self.dsn,uuid4()).token
    rate=fixture.FeedbackTests.rate
    def moderate(self,receipt,*,rating=4,interest="maybe",verdict="eligible",reason="valid_feedback",**kw):
        args=dict(expected_preview_sha256=self.hash,expected_usefulness=rating,
                  expected_interest=interest,verdict=verdict,reason=reason,reviewer_id=self.reviewer)
        return review_feedback(self.dsn,receipt.feedback_id,**(args|kw))

    def test_review_exact_values_terminal_and_owner_status(self):
        r=self.rate()
        self.assertEqual(own_feedback(self.dsn,self.token,r.feedback_id)["moderation"],"pending")
        self.assertFalse(self.moderate(r,rating=5))
        self.assertFalse(self.moderate(r,expected_preview_sha256="b"*64))
        self.assertTrue(self.moderate(r))
        self.assertTrue(self.moderate(r))
        self.assertFalse(self.moderate(r,verdict="rejected",reason="spam"))
        self.assertEqual(own_feedback(self.dsn,self.token,r.feedback_id)["moderation"],"eligible")
        self.assertIsNone(own_feedback(self.dsn,self.other,r.feedback_id))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0],1)

    def test_aggregate_excludes_rejected_pending_withdrawn_and_small_samples(self):
        self.assertEqual(feedback_summary(self.dsn,self.preview)["status"],"insufficient_sample")
        accepted=[]
        for rating,interest in [(5,"yes"),(4,"yes"),(3,"maybe"),(2,"no"),(1,"maybe")]:
            token=issue_session(self.dsn,uuid4()).token
            r=self.rate(token=token,usefulness=rating,purchase_interest=interest)
            self.assertEqual(r.status,"accepted")
            self.assertTrue(self.moderate(r,rating=rating,interest=interest))
            accepted.append((token,r))
        spam=self.rate(token=self.other,usefulness=5,purchase_interest="yes")
        self.assertTrue(self.moderate(spam,rating=5,interest="yes",verdict="rejected",reason="spam"))
        self.assertEqual(self.rate().status,"accepted")
        summary=feedback_summary(self.dsn,self.preview)
        self.assertEqual(summary["eligible_count"],5)
        self.assertEqual(summary["usefulness_sum"],15)
        self.assertEqual(summary["interest"],{"yes":2,"maybe":2,"no":1})
        self.assertTrue(summary["self_reported"])
        self.assertFalse(summary["commercial_authority"])
        self.assertNotIn("member_id",str(summary))
        token,r=accepted[0]
        self.assertTrue(withdraw_feedback(self.dsn,token,r.feedback_id))
        self.assertEqual(feedback_summary(self.dsn,self.preview)["status"],"insufficient_sample")
        self.assertFalse(self.moderate(r,rating=5,interest="yes"))

    def test_withdrawn_preview_suppresses_aggregate_and_new_eligibility(self):
        r=self.rate()
        self.assertTrue(withdraw(self.dsn,self.preview,reviewer_id=self.reviewer,
            evidence_ref="test:withdraw",evidence=b"synthetic withdrawal",confirmed=True))
        self.assertIsNone(feedback_summary(self.dsn,self.preview))
        self.assertFalse(self.moderate(r))
        self.assertTrue(self.moderate(r,verdict="rejected",reason="integrity"))

    def test_terminal_review_frees_pending_not_daily_capacity(self):
        r=self.rate()
        self.assertTrue(self.moderate(r))
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE workshop_feedback SET submitted_at=submitted_at-90000 WHERE id=%s",(r.feedback_id,))
        for i in range(3):
            self.assertEqual(submit_suggestion(self.dsn,self.token,key=str(i),body="Idea "+str(i)).status,"accepted")
        self.assertEqual(submit_suggestion(self.dsn,self.token,key="last",body="Last idea").status,"member_limit")

    def test_identity_drift_disables_moderation_and_aggregate(self):
        r=self.rate()
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertFalse(self.moderate(r))
            self.assertIsNone(feedback_summary(self.dsn,self.preview))
