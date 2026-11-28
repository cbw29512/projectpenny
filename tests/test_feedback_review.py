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
from penny.community.feedback_queue import pending_feedback
from penny.community.intake import submit_suggestion


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class FeedbackReviewTests(fixture.FeedbackFixture):
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

    def test_pending_worklist_is_bounded_private_and_clears_reviewed_rows(self):
        first=self.rate()
        second=self.rate(token=self.other)
        rows=pending_feedback(self.dsn)
        self.assertEqual({r["feedback_id"] for r in rows},{first.feedback_id,second.feedback_id})
        self.assertEqual(len(pending_feedback(self.dsn,limit=1)),1)
        for row in rows:
            self.assertEqual(set(row),{"feedback_id","preview_id","preview_sha256","usefulness",
                "purchase_interest","submitted_at","preview_available"})
            self.assertTrue(row["preview_available"])
        for invalid in (True,0,21):
            with self.assertRaises(ValueError):
                pending_feedback(self.dsn,limit=invalid)
        self.assertTrue(self.moderate(first))
        self.assertEqual([r["feedback_id"] for r in pending_feedback(self.dsn)],[second.feedback_id])
        self.assertTrue(withdraw_feedback(self.dsn,self.other,second.feedback_id))
        self.assertEqual(pending_feedback(self.dsn),())

    def test_stale_preview_worklist_and_guardian(self):
        r=self.rate()
        self.assertTrue(withdraw(self.dsn,self.preview,reviewer_id=self.reviewer,
            evidence_ref="test:withdraw",evidence=b"synthetic withdrawal",confirmed=True))
        self.assertFalse(pending_feedback(self.dsn)[0]["preview_available"])
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertEqual(pending_feedback(self.dsn),())
        self.assertTrue(self.moderate(r,verdict="rejected",reason="integrity"))
        self.assertEqual(pending_feedback(self.dsn),())
