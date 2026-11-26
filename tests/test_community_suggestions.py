"""Screening and private intake regression tests."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4
import psycopg

from database_fixture import DSN, DatabaseFixture
from penny.auth.session import issue_session
from penny.community.intake import submit_suggestion
from penny.community.review import review_suggestion
from penny.community.suggestion_state import screened_text, Verdict, digest


class ScreeningTests(unittest.TestCase):
    def test_normalization_and_owner_duplicate_key(self):
        one = screened_text("a", "  Build   printable sheets  ")
        two = screened_text("b", "build printable sheets")
        self.assertEqual(one[0], "Build printable sheets")
        self.assertEqual(one[2], two[2])
        self.assertNotEqual(one[1], two[1])

    def test_invalid_input(self):
        for body in ("", "!", "x"*501, "hello\x00world", "hi\u200bthere", None):
            with self.assertRaises(ValueError):
                screened_text("a", body)
        with self.assertRaises(ValueError):
            screened_text("../bad", "Make a product")


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class SuggestionTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.token = issue_session(self.dsn, uuid4()).token
        self.reviewer = uuid4()

    def submit(self, key, body, token=None):
        return submit_suggestion(self.dsn, token or self.token, key=key, body=body)

    def review(self, receipt, body, verdict=Verdict.ELIGIBLE, reason="mission_fit"):
        return review_suggestion(self.dsn, receipt.suggestion_id,
            expected_sha256=digest(body), verdict=verdict, reason=reason, reviewer_id=self.reviewer)

    def test_owner_replay_and_no_cross_owner_disclosure(self):
        first = self.submit("a", "Build a template")
        self.assertEqual(first.status, "accepted")
        self.assertEqual(self.submit("a", "Build a template").suggestion_id, first.suggestion_id)
        self.assertEqual(self.submit("a", "Make a calendar").status, "idempotency_conflict")
        self.assertEqual(self.submit("b", "build   a template").status, "duplicate")
        other = issue_session(self.dsn, uuid4()).token
        self.assertNotEqual(self.submit("a", "Build a template", other).suggestion_id, first.suggestion_id)
        with self.assertRaises(PermissionError):
            self.submit("a", "Build a template", "a"*43)

    def test_atomic_quota_concurrent(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda i: self.submit(str(i), "Product idea "+str(i)), range(4)))
        self.assertEqual(sum(r.status == "accepted" for r in results), 3)
        self.assertEqual(sum(r.status == "member_limit" for r in results), 1)

    def test_review_binds_exact_text_no_task_and_no_reversal(self):
        body = "Build printable cards"
        first = self.submit("a", body)
        self.assertFalse(self.review(first, "Other content"))
        self.assertTrue(self.review(first, body))
        self.assertTrue(self.review(first, body))
        self.assertFalse(self.review(first, body, Verdict.REJECTED, "spam"))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT count(*) FROM community_suggestion_review").fetchone()[0], 1)

    def test_drift_fails_closed(self):
        with patch("penny.brain.identity.SYSTEM_PROMPT", "changed"):
            self.assertEqual(self.submit("a", "Build something").status, "denied")
