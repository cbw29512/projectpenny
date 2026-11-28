"""Owner isolation, review visibility and no inference on suggestion status."""
import contextlib
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN, DatabaseFixture
from penny.auth.session import issue_session, revoke_session
from penny.community.intake import submit_suggestion
from penny.community.review import review_suggestion
from penny.community.suggestion_queue import own_status, pending_suggestions
from penny.community.suggestion_state import Verdict, digest
from penny.runtime.community import main


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class SuggestionQueueTests(DatabaseFixture):
    def test_owner_status_and_terminal_review(self):
        token = issue_session(self.dsn, uuid4()).token
        other = issue_session(self.dsn, uuid4()).token
        body = "Create a useful printable calendar"
        receipt = submit_suggestion(self.dsn, token, key="first", body=body)
        result = own_status(self.dsn, token, receipt.suggestion_id)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(set(result), {"suggestion_id","status","reason","submitted_at","reviewed_at"})
        self.assertIsNone(own_status(self.dsn, other, receipt.suggestion_id))
        rows = pending_suggestions(self.dsn)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["body"], body)
        self.assertEqual(rows[0]["body_sha256"], digest(body))
        self.assertTrue(rows[0]["integrity_ok"])
        self.assertNotIn("member_id", rows[0])
        self.assertTrue(review_suggestion(self.dsn, receipt.suggestion_id,
            expected_sha256=rows[0]["body_sha256"], verdict=Verdict.ELIGIBLE,
            reason="mission_fit", reviewer_id=uuid4()))
        self.assertEqual(pending_suggestions(self.dsn), ())
        self.assertEqual(own_status(self.dsn, token, receipt.suggestion_id)["status"], "eligible")
        self.assertTrue(revoke_session(self.dsn, token))
        with self.assertRaises(PermissionError):
            own_status(self.dsn, token, receipt.suggestion_id)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0], 0)

    def test_worklist_bounded_and_identity_drift_denied(self):
        token = issue_session(self.dsn, uuid4()).token
        receipt = submit_suggestion(self.dsn, token, key="one", body="Build a helpful checklist")
        submit_suggestion(self.dsn, token, key="two", body="Build a useful planner")
        self.assertEqual(len(pending_suggestions(self.dsn, limit=1)), 1)
        with self.assertRaises(ValueError):
            pending_suggestions(self.dsn, limit=21)
        with patch("penny.brain.identity.SYSTEM_PROMPT", "changed"):
            self.assertIsNone(own_status(self.dsn, token, receipt.suggestion_id))
            self.assertEqual(pending_suggestions(self.dsn), ())


class CommunityOperatorTests(unittest.TestCase):
    def test_review_requires_confirmation_before_loading_credentials(self):
        args = ["--config","fixture","review",str(uuid4()),"--digest","a"*64,
                "--verdict","eligible","--reason","mission_fit","--reviewer-id",str(uuid4())]
        with patch("penny.runtime.community.load_config") as load:
            self.assertEqual(main(args), 1)
            load.assert_not_called()

    def test_list_reuses_bounded_worklist(self):
        out = io.StringIO()
        with patch("penny.runtime.community.load_config", return_value=SimpleNamespace(dsn="fixture")), \
             patch("penny.runtime.community.pending_suggestions", return_value=()) as pending, \
             contextlib.redirect_stdout(out):
            self.assertEqual(main(["--config","fixture","list","--limit","5"]), 0)
            pending.assert_called_once_with("fixture", limit=5)
        self.assertEqual(json.loads(out.getvalue()), [])
