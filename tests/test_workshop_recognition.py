"""Revision evidence and admission regression; synthetic feedback only."""
import json
import unittest
from unittest.mock import Mock
from uuid import uuid4

import psycopg
import test_showroom_feedback as fixture
from database_fixture import DSN
from penny.auth.session import issue_session
from penny.business.revision import revision_basis,submit_revision
from penny.business.revision_compare import compare_revision
from penny.business.workshop_intake import read_artifact
from penny.business.quality import quality_status,review
from penny.business.quality_state import CRITERIA
from penny.business.revision_review import review_revision,revision_review_status
from penny.community.feedback_review import review_feedback
from penny.community.feedback import withdraw_feedback
from penny.runtime.inference import inference_tick
from penny.runtime.operator_control import start


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class WorkshopRecognitionTests(fixture.FeedbackFixture):
    def seed(self):
        ratings=[]
        for _ in range(5):
            token=issue_session(self.dsn,uuid4()).token
            r=self.rate(token=token)
            self.assertEqual(r.status,"accepted")
            self.assertTrue(review_feedback(self.dsn,r.feedback_id,
                expected_preview_sha256=self.hash,expected_usefulness=4,
                expected_interest="maybe",verdict="eligible",reason="valid_feedback",
                reviewer_id=self.reviewer))
            ratings.append((token,r.feedback_id))
        return ratings

    def request(self,digest,**changes):
        args=dict(expected_basis_sha256=digest,brief="Add a useful weather check",
                  reviewer_id=self.reviewer,evidence_ref="test:revision",
                  evidence=b"synthetic reviewed improvement",confirmed=True)
        return submit_revision(self.dsn,self.preview,**(args|changes))

    def test_reviewed_improvement_requires_exact_current_evidence(self):
        from penny.community.intake import submit_suggestion
        from penny.community.review import review_suggestion
        from penny.community.suggestion_state import Verdict,digest as text_digest
        from penny.recognition.workshop import record_workshop_outcome
        from penny.recognition.member import request_credit,list_credit,withdraw_credit
        from penny.recognition.admin import verify_request
        from penny.recognition.state import Role,CONSENT_VERSION
        contributor=issue_session(self.dsn,uuid4()).token
        suggestion=submit_suggestion(self.dsn,contributor,key="weather",body="Add a weather check")
        source=(suggestion.suggestion_id,text_digest("Add a weather check"))
        ratings=self.seed()
        digest=revision_basis(self.dsn,self.preview)["basis_sha256"]
        self.assertEqual(self.request(digest,suggestions=(source,)).status,"suggestion_unavailable")
        self.assertTrue(review_suggestion(self.dsn,source[0],expected_sha256=source[1],
            verdict=Verdict.ELIGIBLE,reason="mission_fit",reviewer_id=self.reviewer))
        r=self.request(digest,suggestions=(source,))
        self.assertEqual(r.status,"accept")
        self.assertEqual(self.request(digest).status,"idempotency_conflict")
        self.assertIsNone(record_workshop_outcome(self.dsn,r.task_id,reviewer_id=self.reviewer,confirmed=True))
        self.assertTrue(start(self.dsn,"inference",confirmed=True))
        brain=Mock()
        brain.generate.return_value=json.dumps(dict(title="New checklist",instructions="Read first",
            items=["Check weather","Pack layers","Check documents"]))
        self.assertEqual(inference_tick(self.dsn,brain),"completed")
        c=compare_revision(self.dsn,r.task_id)
        args=dict(parent_sha256=c["before"]["sha256"],child_sha256=c["after"]["sha256"],
            basis_sha256=digest,quality_review_id=uuid4(),verdict="improved",
            reviewer_id=self.reviewer,evidence_ref="test:improvement",
            evidence=b"synthetic comparison review",confirmed=True)
        def decide(**changes):
            return review_revision(self.dsn,r.task_id,**(args|changes))
        self.assertFalse(decide())
        q=review(self.dsn,r.task_id,source_ref="test:revision-quality",
            expected_content_sha256=args["child_sha256"],checks={k:True for k in CRITERIA},
            revoked=False,reviewer_id=self.reviewer,evidence_ref="test:quality",
            evidence=b"synthetic quality",confirmed=True)
        args["quality_review_id"]=q.entry_id
        self.assertFalse(decide(parent_sha256="0"*64))
        with self.assertRaises(ValueError):
            decide(confirmed=False)
        self.assertTrue(decide())
        self.assertTrue(decide())
        self.assertFalse(decide(verdict="not_improved"))
        status=revision_review_status(self.dsn,r.task_id)
        self.assertTrue(status["improvement_verified"])
        self.assertFalse(status["commercial_release_authorized"])
        outcome=record_workshop_outcome(self.dsn,r.task_id,reviewer_id=self.reviewer,confirmed=True)
        self.assertIsNotNone(outcome)
        self.assertIsNone(request_credit(self.dsn,self.other,outcome,Role.IDEA,accepted_version=CONSENT_VERSION))
        self.assertIsNone(request_credit(self.dsn,contributor,outcome,Role.TESTING,accepted_version=CONSENT_VERSION))
        consent=request_credit(self.dsn,contributor,outcome,Role.IDEA,accepted_version=CONSENT_VERSION)
        self.assertIsNotNone(consent)
        self.assertEqual(list_credit(self.dsn,contributor),())
        self.assertTrue(verify_request(self.dsn,consent,reviewer_id=self.reviewer,
            evidence_ref="test:attribution",evidence=b"synthetic verified contribution"))
        self.assertEqual(len(list_credit(self.dsn,contributor)),1)
        self.assertTrue(withdraw_feedback(self.dsn,*ratings[0]))
        self.assertEqual(list_credit(self.dsn,contributor),())
        self.assertTrue(withdraw_credit(self.dsn,contributor,consent))
        status=revision_review_status(self.dsn,r.task_id)
        self.assertEqual(status["status"],"stale")
        self.assertFalse(status["improvement_verified"])
        self.assertEqual(status["recorded_verdict"],"improved")
