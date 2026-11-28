"""Disposable PostgreSQL tests for maintenance application and audit."""
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
from penny.memory.review import revoke
from penny.memory.task import submit_informed
from penny.scheduler.outcomes import complete


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class AdjudicationTests(ReviewFixture):
    def stage(self, action="correct", replacement="Measure shipping costs accurately"):
        a = self.candidate("a","Measure shipping outcomes")
        self.assertTrue(self.approve(a,"Measure shipping outcomes"))
        sources = [a]
        if action in ("consolidate","contradiction"):
            b = self.candidate("b","Review shipping invoices")
            self.assertTrue(self.approve(b,"Review shipping invoices"))
            sources.append(b)
        submit_maintenance(self.store,"review","shipping outcomes")
        claim = self.store.claim()
        self.assertEqual({m.source_task_id for m in recall(self.dsn,claim.task_id,claim.fence)},set(sources))
        raw = proposal(action,sources,replacement)
        self.assertTrue(complete(self.dsn,claim.task_id,claim.fence,success=True,result=raw))
        return claim.task_id,sources,raw

    def decide(self, task, raw, choice=ReviewChoice.APPLY, retention=0):
        return adjudicate(self.dsn,task,reviewer_id=self.reviewer,review_ref="review/final",
                          evidence=b"reviewed independent evidence",expected_proposal=raw,
                          choice=choice,retention_seconds=retention)

    def test_correction_preserves_history_and_recall_uses_replacement(self):
        task,sources,raw = self.stage()
        self.assertTrue(self.decide(task,raw,retention=7200))
        self.assertFalse(self.decide(task,raw,retention=7200))
        with psycopg.connect(self.dsn) as conn:
            old = conn.execute("SELECT content,revoked_at,expires_at FROM business_memory WHERE source_task_id=%s",
                               (sources[0],)).fetchone()
            new = conn.execute("SELECT content,revoked_at,expires_at FROM business_memory WHERE source_task_id=%s",
                               (task,)).fetchone()
            self.assertEqual(old[0],"Measure shipping outcomes")
            self.assertIsNotNone(old[1])
            self.assertIsNone(new[1])
            self.assertLessEqual(new[2],old[2])
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory_event").fetchone()[0],3)
        submit_informed(self.store,"after","shipping costs")
        claim = self.store.claim()
        self.assertEqual([m.source_task_id for m in recall(self.dsn,claim.task_id,claim.fence)],[task])

    def test_consolidation_and_outdated(self):
        task,sources,raw = self.stage("consolidate","Measure shipping costs and invoices")
        self.assertTrue(self.decide(task,raw,retention=3600))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory WHERE revoked_at IS NULL").fetchone()[0],1)
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory WHERE revoked_at IS NOT NULL").fetchone()[0],2)

    def test_outdated_retires_without_replacement(self):
        task,_,raw = self.stage("outdated",None)
        self.assertTrue(self.decide(task,raw))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory WHERE revoked_at IS NULL").fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT verdict,replacement_id FROM memory_maintenance_decision").fetchone(),("applied",None))

    def test_contradiction_acknowledgment_does_not_retire(self):
        task,_,raw = self.stage("contradiction",None)
        self.assertFalse(self.decide(task,raw))
        self.assertTrue(self.decide(task,raw,ReviewChoice.ACKNOWLEDGE))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory WHERE revoked_at IS NULL").fetchone()[0],2)

    def test_rejection_and_changed_proposal(self):
        task,sources,raw = self.stage()
        self.assertFalse(self.decide(task,proposal("correct",sources,"changed"),retention=3600))
        self.assertTrue(self.decide(task,raw,ReviewChoice.REJECT))
        self.assertFalse(self.decide(task,raw,retention=3600))

    def test_stale_source_and_guardian_denial(self):
        task,sources,raw = self.stage()
        with patch("penny.memory.adjudication.authorize",return_value=Decision(False,"denied")):
            self.assertFalse(self.decide(task,raw,retention=3600))
        self.assertTrue(revoke(self.dsn,sources[0],reviewer_id=self.reviewer,review_ref="review/revoke"))
        self.assertFalse(self.decide(task,raw,retention=3600))

    def test_audit_failure_rolls_back_all_changes(self):
        task,_,raw = self.stage()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("""CREATE FUNCTION refuse_decision() RETURNS trigger LANGUAGE plpgsql AS $$
                          BEGIN RAISE EXCEPTION 'test'; END; $$""")
            conn.execute("""CREATE TRIGGER refuse_decision BEFORE INSERT ON memory_maintenance_decision
                          FOR EACH ROW EXECUTE FUNCTION refuse_decision()""")
        with self.assertRaises(psycopg.Error):
            self.decide(task,raw,retention=3600)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory").fetchone()[0],1)
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory WHERE revoked_at IS NULL").fetchone()[0],1)
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory_event").fetchone()[0],1)
