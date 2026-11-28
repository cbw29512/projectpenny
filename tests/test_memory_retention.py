"""Disposable PostgreSQL tests for draft expiration and scoped redaction."""
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from memory_review_fixture import DSN, ReviewFixture
from test_memory_maintenance import proposal
from penny.guardian.state import Decision
from penny.memory.adjudication import adjudicate
from penny.memory.adjudication_state import ReviewChoice
from penny.memory.maintenance import submit_maintenance
from penny.memory.recall import recall
from penny.memory.retention import purge_expired
from penny.memory.retention_state import REDACTED
from penny.scheduler.outcomes import complete


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class RetentionTests(ReviewFixture):
    def purge(self,limit=25):
        return purge_expired(self.dsn,reviewer_id=self.reviewer,review_ref="retention/1",limit=limit)

    def expire_candidates(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE memory_candidate SET review_until=to_timestamp(1)")

    def test_expired_candidate_cannot_be_approved_and_is_redacted(self):
        source = self.candidate()
        self.expire_candidates()
        self.assertFalse(self.approve(source))
        self.assertEqual(self.purge().task_ids,(source,))
        self.assertEqual(self.purge().task_ids,())
        self.assertFalse(self.approve(source,REDACTED))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT content FROM memory_candidate").fetchone()[0],REDACTED)
            self.assertEqual(conn.execute("SELECT payload FROM work_task").fetchone()[0],REDACTED)
            self.assertEqual(conn.execute("SELECT result FROM task_outcome").fetchone()[0],REDACTED)
            self.assertEqual(conn.execute("SELECT draft_kind FROM memory_draft_purge_event").fetchone()[0],"candidate")

    def test_approved_history_and_fresh_drafts_untouched(self):
        approved = self.candidate("approved")
        self.assertTrue(self.approve(approved))
        self.expire_candidates()
        self.candidate("fresh")
        self.assertEqual(self.purge().task_ids,())
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM memory_candidate WHERE purged_at IS NULL").fetchone()[0],2)

    def test_batch_limit_and_guardian(self):
        self.candidate("a")
        self.candidate("b")
        self.expire_candidates()
        with patch("penny.memory.retention.authorize",return_value=Decision(False,"denied")):
            self.assertEqual(self.purge().task_ids,())
        with self.assertRaises(ValueError):
            self.purge(True)
        self.assertEqual(len(self.purge(1).task_ids),1)
        self.assertEqual(len(self.purge(1).task_ids),1)
        self.assertEqual(self.purge().task_ids,())

    def test_expired_maintenance_cannot_be_applied_and_sources_survive(self):
        source = self.candidate("a","Measure shipping outcomes")
        self.assertTrue(self.approve(source,"Measure shipping outcomes"))
        submit_maintenance(self.store,"review","shipping")
        claim = self.store.claim()
        self.assertEqual([m.source_task_id for m in recall(self.dsn,claim.task_id,claim.fence)],[source])
        raw = proposal("correct",[source],"Measure shipping costs")
        self.assertTrue(complete(self.dsn,claim.task_id,claim.fence,success=True,result=raw))
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE memory_maintenance_proposal SET review_until=to_timestamp(1)")
        self.assertFalse(adjudicate(self.dsn,claim.task_id,reviewer_id=self.reviewer,
                         review_ref="review/2",evidence=b"evidence",expected_proposal=raw,
                         choice=ReviewChoice.APPLY,retention_seconds=3600))
        self.assertEqual(self.purge().task_ids,(claim.task_id,))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT rationale,replacement FROM memory_maintenance_proposal").fetchone(),
                             (REDACTED,REDACTED))
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory WHERE revoked_at IS NULL").fetchone()[0],1)
            self.assertEqual(conn.execute("SELECT count(*) FROM memory_maintenance_source").fetchone()[0],1)

    def test_failed_audit_rolls_back_redaction(self):
        self.candidate()
        self.expire_candidates()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("DROP TABLE memory_draft_purge_event")
        with self.assertRaises(psycopg.Error):
            self.purge()
        with psycopg.connect(self.dsn) as conn:
            self.assertIsNone(conn.execute("SELECT purged_at FROM memory_candidate").fetchone()[0])
            self.assertNotEqual(conn.execute("SELECT payload FROM work_task").fetchone()[0],REDACTED)
