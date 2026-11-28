"""Hourly adapter uses real scheduler admission; no live model or side effects."""
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN, DatabaseFixture
from penny.business.hourly import plan_hour
from penny.business.review import advance
from penny.business.state import Action, Category, Metric
from penny.business.store import stage


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class HourlyTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer = uuid4()
        self.evidence = b"synthetic reviewed checklist"
        self.q = stage(
            self.dsn, source_ref="hourly-test", category=Category.DIGITAL_PRODUCT,
            title="Planning checklist", hypothesis="Useful private checklist",
            metric=Metric.PROTOTYPE_CHECKS_PASSED, target=3, duration_seconds=600,
            additional_cash_cents=0, evidence_ref="private:test",
            evidence=self.evidence, reviewer_id=self.reviewer,
            review_until=int(time.time())+3600
        ).entry_id
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET enabled=true")

    def step(self, action):
        self.assertTrue(advance(
            self.dsn, self.q, action=action,
            expected_proposal_sha256=sha256(self.evidence).hexdigest(),
            evidence_ref="private:review", evidence=b"synthetic decision",
            reviewer_id=self.reviewer, confirmed=True
        ))

    def start_experiment(self):
        self.step(Action.APPROVE)
        self.step(Action.START)

    def plan(self):
        return plan_hour(self.dsn, reviewer_id=self.reviewer, confirmed=True)

    def count(self, table):
        # Fixed test-owned identifiers only.
        with psycopg.connect(self.dsn) as conn:
            from psycopg import sql
            return conn.execute(sql.SQL("SELECT count(*) FROM {}").format(
                sql.Identifier(table))).fetchone()[0]

    def test_no_self_approval_and_durable_skip(self):
        self.step(Action.APPROVE)
        first = self.plan()
        self.assertEqual(first["outcome"], "no_eligible_work")
        self.step(Action.START)
        self.assertTrue(self.plan()["replayed"])
        self.assertEqual(self.count("work_task"), 0)

    def test_atomic_hourly_admission_and_concurrency(self):
        self.start_experiment()
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda _: self.plan(), range(3)))
        self.assertTrue(all(r["outcome"] == "scheduled" for r in results))
        self.assertEqual(sum(not r["replayed"] for r in results), 1)
        self.assertEqual(len({r["task_id"] for r in results}), 1)
        self.assertEqual(self.count("work_task"), 1)
        self.assertEqual(self.count("workshop_task"), 1)
        self.assertEqual(self.count("hourly_plan"), 1)

    def test_pause(self):
        self.start_experiment()
        self.store.set_paused(True)
        self.assertEqual(self.plan()["outcome"], "paused")
        self.assertEqual(self.count("work_task"), 0)

    def test_uncertain_runtime(self):
        self.start_experiment()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET uncertain=true")
        self.assertEqual(self.plan()["outcome"], "blocked")
        self.assertEqual(self.count("work_task"), 0)

    def test_guardian_and_explicit_confirmation(self):
        self.start_experiment()
        self.assertEqual(plan_hour(self.dsn, reviewer_id=self.reviewer)["outcome"], "denied")
        with patch("penny.brain.identity.SYSTEM_PROMPT", "changed"):
            self.assertEqual(self.plan()["outcome"], "denied")
        self.assertEqual(self.count("hourly_plan"), 0)

    def test_existing_task_blocks_planner(self):
        self.start_experiment()
        self.assertEqual(self.store.submit(None, "existing", "existing work").status, "accept")
        self.assertEqual(self.plan()["outcome"], "busy")
        self.assertEqual(self.count("work_task"), 1)

    def test_existing_prototype_requires_review(self):
        from penny.business.workshop_admission import submit_prototype
        from penny.scheduler.worker import run_once, WorkerResult
        from unittest.mock import Mock
        self.start_experiment()
        r = submit_prototype(self.dsn, self.q, key="manual", reviewer_id=self.reviewer)
        self.assertEqual(r.status, "accept")
        brain = Mock()
        brain.generate.return_value = "invalid prototype"
        self.assertEqual(run_once(self.store, brain), WorkerResult.COMPLETED)
        self.assertEqual(self.plan()["outcome"], "no_eligible_work")
        self.assertEqual(self.count("work_task"), 1)
