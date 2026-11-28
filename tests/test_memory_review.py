"""Reviewed business memory lifecycle integration tests."""
import unittest
from uuid import uuid4
import psycopg
from memory_review_fixture import DSN, CONTENT, ReviewFixture
from penny.memory.recall import recall
from penny.memory.review import revoke

@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class ReviewTests(ReviewFixture):
    def test_quarantine_approval_and_revocation(self):
        source = self.candidate()
        claim = self.claim()
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence), ())
        self.assertTrue(self.approve(source))
        self.assertFalse(self.approve(source))
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence)[0].content,CONTENT)
        self.assertTrue(revoke(self.dsn,source,reviewer_id=self.reviewer,review_ref="review/2"))
        self.assertFalse(revoke(self.dsn,source,reviewer_id=self.reviewer,review_ref="review/2"))
        self.assertFalse(self.approve(source))
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence), ())
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory_event").fetchone()[0],2)

    def test_missing_candidate_and_mismatched_snapshot(self):
        self.assertFalse(self.approve(uuid4()))
        self.assertFalse(self.approve(self.candidate(), "changed"))
        with self.assertRaises(ValueError):
            self.approve(uuid4(), evidence=b"")
        with self.assertRaises(ValueError):
            self.approve(uuid4(), reviewer_id="forged")
        with self.assertRaises(ValueError):
            self.approve(uuid4(), retention_seconds=True)

    def test_public_claim_cannot_recall(self):
        self.assertTrue(self.approve(self.candidate()))
        claim = self.claim(uuid4())
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence), ())

    def test_stale_fence_pause_and_expired_memory(self):
        source = self.candidate()
        self.assertTrue(self.approve(source))
        claim = self.claim()
        self.assertEqual(recall(self.dsn,claim.task_id,uuid4()), ())
        self.store.set_paused(True)
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence), ())
        self.store.set_paused(False)
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE business_memory SET approved_at=1,expires_at=2")
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence), ())

    def test_bounded_complete_records(self):
        for i in range(4):
            content = "Measure " + str(i) + "x" * 791
            self.assertTrue(self.approve(self.candidate(str(i),content),content))
        claim = self.claim()
        records = recall(self.dsn,claim.task_id,claim.fence)
        self.assertEqual(len(records),1)
        self.assertEqual(len(records[0].content),800)

    def test_approval_atomic_with_audit(self):
        source = self.candidate()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("DROP TABLE business_memory_event")
        with self.assertRaises(psycopg.Error):
            self.approve(source)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory").fetchone()[0],0)


    def test_informed_worker_gets_only_approved_memory(self):
        from unittest.mock import Mock
        from penny.memory.task import submit_informed
        from penny.scheduler.worker import run_once, WorkerResult

        source = self.candidate("approved")
        self.assertTrue(self.approve(source))
        self.candidate("unapproved")
        submit_informed(self.store,"work","Measure outcomes")
        brain = Mock()
        brain.generate_with_memory.return_value = "Private draft"
        self.assertEqual(run_once(self.store,brain),WorkerResult.COMPLETED)
        task, budget, records = brain.generate_with_memory.call_args.args
        self.assertEqual(task,"Measure outcomes")
        self.assertGreater(budget,0)
        self.assertEqual([m.source_task_id for m in records],[source])
        brain.generate.assert_not_called()

    def test_member_prefix_and_ordinary_task_do_not_enable_memory(self):
        from unittest.mock import Mock
        from penny.scheduler.worker import run_once, WorkerResult

        self.assertTrue(self.approve(self.candidate()))
        for member, key in ((uuid4(),"memory-informed:forged"),(None,"ordinary")):
            self.store.submit(member,key,"Private draft request")
            brain = Mock()
            brain.generate.return_value = "Private draft"
            self.assertEqual(run_once(self.store,brain),WorkerResult.COMPLETED)
            brain.generate.assert_called_once()
            brain.generate_with_memory.assert_not_called()
