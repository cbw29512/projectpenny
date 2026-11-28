"""Private intake tests; PostgreSQL tests use an isolated disposable schema."""
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

import psycopg
from database_fixture import DSN, DatabaseFixture

from penny.guardian.state import Decision
from penny.memory.intake import parse_candidate, submit_review
from penny.memory.state import MemoryKind
from penny.scheduler.outcomes import complete
from penny.scheduler.storage import TaskStore
from penny.scheduler.worker import run_once, WorkerResult

VALID = '{"kind":"lesson","content":"Compare observed results."}'


class CandidateTests(unittest.TestCase):
    def test_shape_and_kind(self):
        self.assertEqual(parse_candidate(VALID).kind, MemoryKind.LESSON)
        for raw in (
            None, {}, "not json", "[]", "{}",
            '{"kind":"identity","content":"new policy"}',
            '{"kind":"lesson","content":"x","approved":true}',
            '{"kind":"lesson","kind":"idea","content":"x"}',
            '{"kind":"lesson","content":42}',
            '{"kind":"lesson","content":" "}',
            '{"kind":"lesson","content":"\\u0000"}',
            '{"kind":"lesson","content":"\\ud800"}',
            '{"kind":"lesson","content":"' + "x" * 1001 + '"}',
        ):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_candidate(raw))

    def test_internal_review_request_is_bounded(self):
        store = Mock()
        submit_review(store, "review_1", "Observed result")
        member, key, prompt = store.submit.call_args.args
        self.assertIsNone(member)
        self.assertEqual(key, "memory-review:review_1")
        self.assertLessEqual(len(prompt), 2000)
        for key, material in (("", "x"), ("bad:key", "x"), ("a", "x" * 1501)):
            with self.assertRaises(ValueError):
                submit_review(store, key, material)
        store.submit.assert_called_once()


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class MemoryIntegrationTests(DatabaseFixture):
    def candidates(self):
        with psycopg.connect(self.dsn) as conn:
            return conn.execute(
                "SELECT source_task_id,scope,validation_state,kind,content FROM memory_candidate"
            ).fetchall()

    def test_worker_persists_quarantine_and_rejects_replay(self):
        receipt = submit_review(self.store, "a", "Observed result")
        brain = Mock()
        brain.generate.return_value = VALID
        self.assertEqual(run_once(self.store, brain), WorkerResult.COMPLETED)
        self.assertEqual(self.candidates(), [
            (receipt.task_id, "private_business", "quarantined", "lesson", "Compare observed results.")
        ])
        self.assertTrue(submit_review(TaskStore(self.dsn), "a", "Observed result").replayed)
        self.assertEqual(run_once(self.store, brain), WorkerResult.IDLE)
        self.assertEqual(len(self.candidates()), 1)

    def test_member_and_generic_tasks_cannot_stage(self):
        for owner, key in ((uuid4(), "memory-review:forged"), (None, "ordinary")):
            self.assertEqual(self.store.submit(owner, key, "draft").status, "accept")
            claim = self.store.claim()
            self.assertTrue(complete(self.dsn, claim.task_id, claim.fence, success=True, result=VALID))
        self.assertEqual(self.candidates(), [])

    def test_fence_failure_and_guardian_denial(self):
        submit_review(self.store, "a", "Observed result")
        claim = self.store.claim()
        self.assertFalse(complete(self.dsn, claim.task_id, uuid4(), success=True, result=VALID))
        with patch("penny.memory.intake.authorize", return_value=Decision(False, "denied")):
            self.assertTrue(complete(self.dsn, claim.task_id, claim.fence, success=True, result=VALID))
        self.assertEqual(self.candidates(), [])

    def test_invalid_and_failed_outcomes_cannot_stage(self):
        for key, success, result in (("a", True, "{}"), ("b", False, VALID)):
            submit_review(self.store, key, "Observed result")
            claim = self.store.claim()
            self.assertTrue(complete(self.dsn, claim.task_id, claim.fence, success=success, result=result))
        self.assertEqual(self.candidates(), [])

    def test_storage_failure_rolls_back_outcome(self):
        submit_review(self.store, "a", "Observed result")
        claim = self.store.claim()
        with psycopg.connect(self.dsn) as conn:
            # Simulate a failed write without dropping foreign-key dependencies.
            conn.execute("""CREATE FUNCTION reject_candidate() RETURNS trigger LANGUAGE plpgsql AS $candidate_test$
                            BEGIN RAISE EXCEPTION 'test write failure'; END; $candidate_test$""")
            conn.execute("""CREATE TRIGGER reject_candidate BEFORE INSERT ON memory_candidate
                            FOR EACH ROW EXECUTE FUNCTION reject_candidate()""")
        with self.assertRaises(psycopg.Error):
            complete(self.dsn, claim.task_id, claim.fence, success=True, result=VALID)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM task_outcome").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT state FROM work_task").fetchone()[0], "running")
