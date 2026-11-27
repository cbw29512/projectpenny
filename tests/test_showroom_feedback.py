"""Local showroom feedback rehearsal; no public routes or model calls."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

import psycopg
import time
from hashlib import sha256
from unittest.mock import Mock
from test_workshop import RAW
from penny.business.store import stage
from penny.business.state import Category,Metric,Action
from penny.business.review import advance
from penny.business.workshop_admission import submit_prototype
from penny.business.workshop_intake import read_artifact
from penny.business.preview import approve
from penny.scheduler.worker import run_once,WorkerResult
from database_fixture import DSN,DatabaseFixture
from penny.auth.session import issue_session
from penny.business.preview import read_preview,withdraw
from penny.community.feedback import submit_feedback,own_feedback,withdraw_feedback
from penny.community.intake import submit_suggestion
from penny.community.feedback_state import validate_feedback


class FeedbackShapeTests(unittest.TestCase):
    def test_rejects_boolean_rating_and_invalid_choices(self):
        for rating,interest in ((True,"yes"),(0,"yes"),(6,"no"),(3,"buy")):
            with self.assertRaises(ValueError):
                validate_feedback(uuid4(),"a"*64,"valid",rating,interest)


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class FeedbackFixture(DatabaseFixture):
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

    def rate(self,token=None,**kw):
        args=dict(preview_id=self.preview,preview_sha256=self.hash,
                  key="rate",usefulness=4,purchase_interest="maybe")
        return submit_feedback(self.dsn,token or self.token,**(args|kw))


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class FeedbackTests(FeedbackFixture):
    def test_owner_only_replay_and_no_work(self):
        r=self.rate()
        self.assertEqual(r.status,"accepted")
        self.assertTrue(self.rate().replay)
        self.assertEqual(self.rate(usefulness=5).status,"idempotency_conflict")
        self.assertEqual(self.rate(key="another").status,"already_rated")
        self.assertIsNone(own_feedback(self.dsn,self.other,r.feedback_id))
        self.assertFalse(withdraw_feedback(self.dsn,self.other,r.feedback_id))
        self.assertEqual(own_feedback(self.dsn,self.token,r.feedback_id)["usefulness"],4)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0],1)
            self.assertEqual(conn.execute("SELECT count(*) FROM workshop_feedback").fetchone()[0],1)

    def test_shared_limit_and_concurrent_duplicate(self):
        for i in range(2):
            self.assertEqual(submit_suggestion(self.dsn,self.token,key=str(i),body="Idea "+str(i)).status,"accepted")
        with ThreadPoolExecutor(max_workers=3) as pool:
            rows=list(pool.map(lambda n:self.rate(key="rate"+str(n)),range(3)))
        self.assertEqual(sum(r.status=="accepted" for r in rows),1)
        self.assertEqual(submit_suggestion(self.dsn,self.token,key="last",body="Another idea").status,"member_limit")

    def test_withdrawal_scrubs_rating_during_identity_drift(self):
        r=self.rate()
        self.store.set_paused(True)
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertTrue(withdraw_feedback(self.dsn,self.token,r.feedback_id))
        row=own_feedback(self.dsn,self.token,r.feedback_id)
        self.assertIsNone(row["usefulness"])
        self.assertIsNone(row["purchase_interest"])
        self.assertIsNotNone(row["withdrawn_at"])
        self.assertEqual(self.rate().status,"withdrawn")
        self.assertFalse(withdraw_feedback(self.dsn,self.token,r.feedback_id))

    def test_exact_version_and_withdrawn_preview(self):
        self.assertEqual(self.rate(preview_sha256="b"*64).status,"unavailable")
        self.assertTrue(withdraw(self.dsn,self.preview,reviewer_id=self.reviewer,
            evidence_ref="test:withdraw",evidence=b"synthetic withdrawal",confirmed=True))
        self.assertEqual(self.rate().status,"unavailable")
        with self.assertRaises(PermissionError):
            self.rate(token="a"*43)
