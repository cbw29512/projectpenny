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
from penny.business.quality import quality_status
from penny.community.feedback_review import review_feedback
from penny.community.feedback import withdraw_feedback
from penny.runtime.inference import inference_tick
from penny.runtime.operator_control import start


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class RevisionTests(fixture.FeedbackFixture):
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

    def test_exact_reviewed_revision_and_private_new_artifact(self):
        self.seed()
        digest=revision_basis(self.dsn,self.preview)["basis_sha256"]
        original=read_artifact(self.dsn,self.task)
        r=self.request(digest)
        self.assertEqual(r.status,"accept")
        self.assertEqual(compare_revision(self.dsn,r.task_id)["status"],"queued")
        self.assertTrue(self.request(digest).replayed)
        self.assertEqual(self.request(digest,brief="Changed brief").status,"idempotency_conflict")
        self.assertTrue(start(self.dsn,"inference",confirmed=True))
        brain=Mock()
        brain.generate.return_value=json.dumps(dict(title="Revised checklist",
            instructions="Review each item",items=["Check weather","Pack documents","Pack layers"]))
        self.assertEqual(inference_tick(self.dsn,brain),"completed")
        revised=read_artifact(self.dsn,r.task_id)
        self.assertEqual(revised["status"],"private_prototype")
        self.assertNotEqual(revised["artifact"]["content_sha256"],original["artifact"]["content_sha256"])
        self.assertEqual(read_artifact(self.dsn,self.task),original)
        self.assertEqual(quality_status(self.dsn,r.task_id)["status"],"unreviewed")
        comparison=compare_revision(self.dsn,r.task_id)
        self.assertEqual(comparison["status"],"available")
        self.assertEqual(comparison["before"]["sha256"],original["artifact"]["content_sha256"])
        self.assertEqual(comparison["after"]["sha256"],revised["artifact"]["content_sha256"])
        self.assertTrue(comparison["comparison"]["title_changed"])
        self.assertTrue(comparison["comparison"]["content_changed"])
        self.assertTrue(comparison["basis_current"])
        self.assertFalse(comparison["improvement_verified"])
        self.assertFalse(comparison["commercial_release_authorized"])
        self.assertIsNone(compare_revision(self.dsn,self.task))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT parent_task_id,preview_id,basis_sha256 FROM workshop_revision").fetchall(),
                             [(self.task,self.preview,digest)])
            self.assertEqual(conn.execute("SELECT count(*) FROM vault_entry").fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0],2)

    def test_stale_or_insufficient_feedback_never_creates_work(self):
        self.assertIsNone(revision_basis(self.dsn,self.preview))
        self.assertEqual(self.request("a"*64).status,"feedback_unavailable")
        ratings=self.seed()
        digest=revision_basis(self.dsn,self.preview)["basis_sha256"]
        with self.assertRaises(ValueError):
            self.request(digest,confirmed=False)
        self.assertTrue(withdraw_feedback(self.dsn,*ratings[0]))
        self.assertEqual(self.request(digest).status,"feedback_unavailable")
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM workshop_revision").fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0],1)

    def test_shared_workshop_gate(self):
        self.seed()
        digest=revision_basis(self.dsn,self.preview)["basis_sha256"]
        self.store.set_paused(True)
        self.assertEqual(self.request(digest).status,"experiment_unavailable")
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM workshop_revision").fetchone()[0],0)

    def test_comparison_refuses_corrupt_admitted_prompt(self):
        self.seed()
        r=self.request(revision_basis(self.dsn,self.preview)["basis_sha256"])
        self.assertEqual(r.status,"accept")
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE work_task SET payload='changed' WHERE id=%s",(r.task_id,))
        result=compare_revision(self.dsn,r.task_id)
        self.assertEqual(result["status"],"integrity_error")
        self.assertIsNone(result["comparison"])
        self.assertNotIn("before",result)
