"""Exact local disclosure from synthetic product evidence."""
import unittest
from unittest.mock import patch
from uuid import uuid4
import test_showroom_feedback as fixture
from database_fixture import DSN
from penny.business.quality import review
from penny.business.quality_state import CRITERIA
from penny.business.catalog import register,withdraw as withdraw_product
from penny.business.preview import withdraw
from penny.progress.workshop_source import TITLE,unavailable
from penny.progress.workshop_snapshot import preview,record,browser_candidate


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class WorkshopSnapshotTests(fixture.FeedbackFixture):
    def setUp(self):
        super().setUp()
        self.quality=review(self.dsn,self.task,source_ref="test:quality-progress",
            expected_content_sha256=self.digest,checks={k:True for k in CRITERIA},
            revoked=False,reviewer_id=self.reviewer,evidence_ref="test:quality",
            evidence=b"synthetic quality",confirmed=True).entry_id
        self.product=register(self.dsn,self.task,source_ref="test:catalog-progress",
            review_id=self.quality,content_sha256=self.digest,title=TITLE,
            reviewer_id=self.reviewer,evidence_ref="test:catalog",
            evidence=b"synthetic catalog review",confirmed=True).entry_id

    def disclose(self,stage,ref,preview_id=None,**changes):
        candidate=preview(self.dsn,self.product,stage=stage,preview_id=preview_id)
        args=dict(stage=stage,preview_id=preview_id,source_ref=ref,
            expected_digest=candidate["source_sha256"],reviewer_id=self.reviewer,
            evidence_ref="test:disclose",evidence=b"synthetic disclosure",confirmed=True)
        return record(self.dsn,self.product,**(args|changes))

    def test_reviewed_exact_candidate_and_withdrawal_no_fallback(self):
        self.assertEqual(browser_candidate(self.dsn),unavailable())
        self.assertIsNone(self.disclose("prototype_reviewed","bad",expected_digest="0"*64))
        with self.assertRaises(ValueError):
            self.disclose("prototype_reviewed","bad",confirmed=False)
        self.assertIsNotNone(self.disclose("prototype_reviewed","prototype"))
        self.assertTrue(self.disclose("prototype_reviewed","prototype").replayed)
        self.assertEqual(browser_candidate(self.dsn)["stage"],"prototype_reviewed")
        self.assertIsNotNone(self.disclose("preview_reviewed","preview",self.preview))
        candidate=browser_candidate(self.dsn)
        self.assertEqual(set(candidate),{"schema","status","product","stage","generated_at","expires_at"})
        self.assertEqual(candidate["stage"],"preview_reviewed")
        self.assertLessEqual(candidate["expires_at"],self.args["expires_at"])
        self.assertTrue(withdraw(self.dsn,self.preview,reviewer_id=self.reviewer,
            evidence_ref="test:withdraw",evidence=b"synthetic",confirmed=True))
        self.assertEqual(browser_candidate(self.dsn),unavailable())
        self.assertIsNotNone(self.disclose("review_withdrawn","correction",self.preview))
        self.assertEqual(browser_candidate(self.dsn)["stage"],"review_withdrawn")

    def test_wrong_source_and_identity_drift(self):
        self.assertIsNone(preview(self.dsn,uuid4(),stage="prototype_reviewed"))
        self.assertIsNone(preview(self.dsn,self.product,stage="preview_reviewed",preview_id=uuid4()))
        self.assertIsNone(preview(self.dsn,self.product,stage="revision_reviewed"))
        self.assertIsNone(preview(self.dsn,self.product,stage="review_withdrawn"))
        self.assertIsNotNone(self.disclose("prototype_reviewed","prototype"))
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertEqual(browser_candidate(self.dsn),unavailable())
        self.assertTrue(withdraw_product(self.dsn,self.product,reviewer_id=self.reviewer,
            evidence_ref="test:withdraw",evidence=b"synthetic",confirmed=True))
        self.assertEqual(browser_candidate(self.dsn),unavailable())
        self.assertIsNotNone(self.disclose("review_withdrawn","correction"))
        self.assertEqual(browser_candidate(self.dsn)["stage"],"review_withdrawn")
