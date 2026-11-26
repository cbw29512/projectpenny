"""Real disposable PostgreSQL; synthetic ledger, not real achievements."""
import time
import unittest
from hashlib import sha256
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN,DatabaseFixture
from penny.progress.achievement_state import Achievement as A
from penny.progress.achievements import preview,review,browser_candidate
from penny.progress.snapshot import preview as snapshot_preview,record_snapshot
from penny.vault.journal import record
from penny.vault.reconciliation import reconcile
from penny.vault.state import Kind
from penny.business.store import stage
from penny.business.state import Category,Metric,Action
from penny.business.review import advance
from penny.progress.timeline import preview_event,record_event,suppress


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class AchievementTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        self.t=int(time.time())-5

    def post(self,kind,cents,ref,**kw):
        return record(self.dsn,source_ref=ref,kind=kind,cents=cents,occurred_at=self.t,
                      evidence_ref="private:"+ref,evidence=b"synthetic",reviewer_id=self.reviewer,
                      **kw).entry_id

    def finance(self,cash,ref="one"):
        reconcile(self.dsn,source_ref="statement:"+ref,statement_at=self.t,
            observed_cash=cash,evidence_ref="private:statement",evidence=b"synthetic statement",
            reviewer_id=self.reviewer,coverage_confirmed=True)
        p=snapshot_preview(self.dsn,finance=True)
        record_snapshot(self.dsn,source_ref="snapshot:"+ref,expected_digest=p["digest"],
            finance=True,business=False,reviewer_id=self.reviewer,evidence_ref="private:review",
            evidence=b"synthetic disclosure",confirmed=True)

    def approve(self,code,ref="award:one",**kw):
        candidate=preview(self.dsn,code)
        args=dict(source_ref=ref,expected_digest=candidate["source_digest"] or "0"*64,
                  approved=True,reviewer_id=self.reviewer,evidence_ref="private:award",
                  evidence=b"synthetic review",confirmed=True)
        return review(self.dsn,code,**(args|kw))

    def state(self,code):
        return next(x["status"] for x in browser_candidate(self.dsn)["achievements"]
                    if x["code"]==code.value)

    def test_support_and_funding_never_unlock_earnings(self):
        self.post(Kind.COMMUNITY_SUPPORT,10000,"support")
        self.post(Kind.FOUNDER_FUNDING,1000,"funding")
        self.finance(11000)
        for code in (A.FIRST_DOLLAR,A.IN_THE_GREEN):
            self.assertFalse(preview(self.dsn,code)["eligible"])
            self.assertIsNone(self.approve(code))
            self.assertEqual(self.state(code),"unverified")

    def test_first_dollar_and_positive_result_are_distinct(self):
        self.post(Kind.COMMERCIAL_RECEIPT,100,"sale")
        self.post(Kind.FOUNDER_PAID_EXPENSE,200,"cost")
        self.finance(100)
        self.assertTrue(preview(self.dsn,A.FIRST_DOLLAR)["eligible"])
        self.assertFalse(preview(self.dsn,A.IN_THE_GREEN)["eligible"])
        self.assertEqual(self.state(A.FIRST_DOLLAR),"unverified")
        self.assertIsNotNone(self.approve(A.FIRST_DOLLAR))
        self.assertEqual(self.state(A.FIRST_DOLLAR),"verified")
        self.assertNotIn("private",str(browser_candidate(self.dsn)))

    def test_refund_and_new_snapshot_invalidate_old_review(self):
        self.post(Kind.COMMERCIAL_RECEIPT,200,"sale")
        self.finance(200)
        self.assertIsNotNone(self.approve(A.IN_THE_GREEN))
        self.post(Kind.COMMERCIAL_REFUND,200,"refund")
        self.assertEqual(self.state(A.IN_THE_GREEN),"needs_review")
        self.finance(0,"two")
        self.assertFalse(preview(self.dsn,A.IN_THE_GREEN)["eligible"])

    def test_review_replay_withdrawal_and_exact_binding(self):
        self.post(Kind.COMMERCIAL_RECEIPT,100,"sale")
        self.finance(100)
        code=A.FIRST_DOLLAR
        digest=preview(self.dsn,code)["source_digest"]
        self.assertIsNone(self.approve(code,expected_digest="0"*64))
        first=self.approve(code)
        self.assertTrue(self.approve(code).replayed)
        self.assertIsNotNone(self.approve(code,"award:withdraw",approved=False,
                                         expected_digest=digest))
        self.assertEqual(self.state(code),"withdrawn")
        self.assertEqual(self.approve(code).entry_id,first.entry_id)
        self.assertEqual(self.state(code),"withdrawn")
        with self.assertRaises(ValueError):
            self.approve(code,evidence=b"changed")

    def test_proof_of_concept_requires_reviewed_unsuppressed_outcome(self):
        evidence=b"synthetic proposal"
        q=stage(self.dsn,source_ref="idea",category=Category.DIGITAL_PRODUCT,title="Checklist",
            hypothesis="One check",metric=Metric.PROTOTYPE_CHECKS_PASSED,target=1,
            duration_seconds=600,additional_cash_cents=0,evidence_ref="private:idea",
            evidence=evidence,reviewer_id=self.reviewer,review_until=self.t+3600).entry_id
        for action in (Action.APPROVE,Action.START,Action.MEASURE):
            args=dict(observed_at=int(time.time()),measured_count=1) if action is Action.MEASURE else {}
            self.assertTrue(advance(self.dsn,q,action=action,expected_proposal_sha256=sha256(evidence).hexdigest(),
                reviewer_id=self.reviewer,evidence_ref="private:decision",evidence=b"synthetic",confirmed=True,**args))
        self.assertFalse(preview(self.dsn,A.PROOF_OF_CONCEPT)["eligible"])
        with psycopg.connect(self.dsn) as conn:
            event=conn.execute("SELECT id FROM business_experiment_event WHERE opportunity_id=%s AND action='measured'",
                               (q,)).fetchone()[0]
        receipt=record_event(self.dsn,event,source_ref="timeline:one",
            expected_digest=preview_event(self.dsn,event)["source_digest"],reviewer_id=self.reviewer,
            evidence_ref="private:timeline",evidence=b"synthetic",confirmed=True)
        self.assertIsNotNone(self.approve(A.PROOF_OF_CONCEPT))
        self.assertEqual(self.state(A.PROOF_OF_CONCEPT),"verified")
        self.assertTrue(suppress(self.dsn,receipt.entry_id,reviewer_id=self.reviewer,
            evidence_ref="private:correction",evidence=b"synthetic",confirmed=True))
        self.assertEqual(self.state(A.PROOF_OF_CONCEPT),"needs_review")

    def test_identity_drift_and_immutable_review(self):
        self.post(Kind.COMMERCIAL_RECEIPT,100,"sale")
        self.finance(100)
        self.approve(A.FIRST_DOLLAR)
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(preview(self.dsn,A.FIRST_DOLLAR))
            self.assertEqual(browser_candidate(self.dsn)["status"],"unavailable")
        with psycopg.connect(self.dsn) as conn:
            with self.assertRaises(psycopg.errors.RaiseException):
                conn.execute("DELETE FROM achievement_review")
            conn.rollback()
