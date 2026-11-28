"""Disposable PostgreSQL timeline with synthetic reviewed business outcomes."""
import time
import unittest
from hashlib import sha256
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN,DatabaseFixture
from penny.business.store import stage
from penny.business.review import advance
from penny.business.state import Category,Metric,Action
from penny.progress.timeline import preview_event,record_event,suppress
from penny.progress.timeline_read import recent


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class TimelineTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()

    def experiment(self,terminal,count=0):
        evidence=b"synthetic private proposal"
        q=stage(self.dsn,source_ref=str(uuid4()),category=Category.DIGITAL_PRODUCT,
            title="PRIVATE TITLE",hypothesis="PRIVATE HYPOTHESIS",
            metric=Metric.PROTOTYPE_CHECKS_PASSED,target=5,duration_seconds=600,
            additional_cash_cents=0,evidence_ref="private:proposal",evidence=evidence,
            reviewer_id=self.reviewer,review_until=int(time.time())+3600).entry_id
        actions=(terminal,) if terminal is Action.REJECT else (Action.APPROVE,Action.START,terminal)
        for action in actions:
            args=dict(observed_at=int(time.time()),measured_count=count) if action is Action.MEASURE else {}
            self.assertTrue(advance(self.dsn,q,action=action,
                expected_proposal_sha256=sha256(evidence).hexdigest(),
                reviewer_id=self.reviewer,evidence_ref="private:decision",
                evidence=b"synthetic decision",confirmed=True,**args))
        with psycopg.connect(self.dsn) as conn:
            return conn.execute("SELECT id FROM business_experiment_event WHERE opportunity_id=%s AND action=%s",
                (q,terminal.value)).fetchone()[0]

    def review(self,event,ref="timeline:1",**kw):
        preview=preview_event(self.dsn,event)
        args=dict(source_ref=ref,expected_digest=preview["source_digest"],
                  reviewer_id=self.reviewer,evidence_ref="private:review",
                  evidence=b"synthetic disclosure review",confirmed=True)
        return record_event(self.dsn,event,**(args|kw))

    def test_no_data_and_unreviewed_source_hidden(self):
        self.assertEqual(recent(self.dsn)["status"],"unavailable")
        event=self.experiment(Action.MEASURE,5)
        self.assertEqual(preview_event(self.dsn,event)["event"]["kind"],"target_met")
        self.assertEqual(recent(self.dsn)["events"],[])
        self.assertIsNone(preview_event(self.dsn,uuid4()))

    def test_all_terminal_outcomes_and_no_private_fields(self):
        for i,(action,count) in enumerate(((Action.MEASURE,5),(Action.MEASURE,0),
                                          (Action.STOP,0),(Action.REJECT,0))):
            self.review(self.experiment(action,count),"timeline:"+str(i))
        events=recent(self.dsn)["events"]
        self.assertEqual({e["kind"] for e in events},
            {"target_met","target_missed","experiment_stopped","experiment_rejected"})
        for e in events:
            self.assertEqual(set(e),{"kind","day_epoch"})
            self.assertEqual(e["day_epoch"]%86400,0)
        self.assertNotIn("PRIVATE",str(events))
        self.assertEqual(len(recent(self.dsn,limit=2)["events"]),2)

    def test_exact_review_and_replay(self):
        event=self.experiment(Action.STOP)
        self.assertIsNone(self.review(event,expected_digest="0"*64))
        receipt=self.review(event)
        self.assertEqual(self.review(event).entry_id,receipt.entry_id)
        self.assertTrue(self.review(event).replayed)
        self.assertIsNone(self.review(event,"timeline:duplicate"))
        with self.assertRaises(ValueError):
            self.review(event,evidence=b"changed")

    def test_suppression_does_not_reactivate_on_replay(self):
        event=self.experiment(Action.MEASURE,5)
        receipt=self.review(event)
        args=dict(reviewer_id=self.reviewer,evidence_ref="private:correction",
                  evidence=b"synthetic correction",confirmed=True)
        self.assertTrue(suppress(self.dsn,receipt.entry_id,**args))
        self.assertFalse(suppress(self.dsn,receipt.entry_id,**args))
        self.assertTrue(self.review(event).replayed)
        self.assertEqual([e["kind"] for e in recent(self.dsn)["events"]],["corrected"])

    def test_nonterminal_event_refused(self):
        event=self.experiment(Action.STOP)
        with psycopg.connect(self.dsn) as conn:
            approved=conn.execute("""SELECT e.id FROM business_experiment_event e
                WHERE e.action='approved' AND e.opportunity_id=
                (SELECT opportunity_id FROM business_experiment_event WHERE id=%s)""",
                (event,)).fetchone()[0]
        self.assertIsNone(preview_event(self.dsn,approved))
        self.assertIsNone(record_event(self.dsn,approved,source_ref="invalid",
            expected_digest="a"*64,reviewer_id=self.reviewer,evidence_ref="private:review",
            evidence=b"synthetic",confirmed=True))

    def test_identity_drift_and_immutable_history(self):
        event=self.experiment(Action.STOP)
        self.review(event)
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(preview_event(self.dsn,event))
            self.assertEqual(recent(self.dsn)["status"],"unavailable")
        with psycopg.connect(self.dsn) as conn:
            with self.assertRaises(psycopg.errors.RaiseException):
                conn.execute("DELETE FROM progress_timeline_event")
            conn.rollback()

    def test_browser_candidate_expiry_and_correction(self):
        from penny.progress.timeline_read import browser_candidate
        self.assertEqual(browser_candidate(self.dsn),recent(self.dsn))
        event=self.experiment(Action.MEASURE,0)
        receipt=self.review(event)
        candidate=browser_candidate(self.dsn)
        self.assertEqual(candidate["status"],"reviewed")
        self.assertEqual(candidate["expires_at"]-candidate["generated_at"],3600)
        self.assertEqual(candidate["events"][0]["kind"],"target_missed")
        self.assertTrue(suppress(self.dsn,receipt.entry_id,reviewer_id=self.reviewer,
            evidence_ref="private:correction",evidence=b"synthetic",confirmed=True))
        self.assertEqual(browser_candidate(self.dsn)["events"][0]["kind"],"corrected")
        self.assertNotIn("private",str(candidate))
