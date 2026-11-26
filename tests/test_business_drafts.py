"""Structured proposal generation via the real fenced queue; fake model only."""
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock,patch
from uuid import uuid4

from database_fixture import DSN,DatabaseFixture
from penny.business.draft_admission import submit_draft
from penny.business.draft_parse import parse_draft
from penny.business.draft_intake import draft_status
from penny.scheduler.worker import run_once,WorkerResult
from penny.scheduler.outcomes import complete
from penny.business.draft_state import DRAFT_PREFIX

VALID=dict(category="digital_product",title="Private checklist",
           hypothesis="Five prototype checks pass",metric="prototype_checks_passed",
           target=5,duration_seconds=600,additional_cash_cents=0)


class ParseTests(unittest.TestCase):
    def test_shape(self):
        self.assertEqual(parse_draft(json.dumps(VALID)).target,5)
        for value in ({**VALID,"additional_cash_cents":1},{**VALID,"target":True},
                      {**VALID,"extra":"tool"},{**VALID,"category":"unknown"},
                      {**VALID,"hypothesis":"\u0000"},{**VALID,"duration_seconds":0}):
            self.assertIsNone(parse_draft(json.dumps(value)))
        self.assertIsNone(parse_draft('{"target":1,"target":2}'))


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class DraftTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()

    def submit(self,key="one",brief="Explore a checklist",**kw):
        args=dict(key=key,brief=brief,reviewer_id=self.reviewer)
        return submit_draft(self.dsn,**(args|kw))

    def finish(self,raw):
        brain=Mock()
        brain.generate.return_value=raw
        self.assertEqual(run_once(self.store,brain),WorkerResult.COMPLETED)
        brain.generate.assert_called_once()
        return brain

    def test_real_queue_quarantines_no_opportunity_or_revenue(self):
        receipt=self.submit()
        self.assertEqual(receipt.status,"accept")
        self.assertEqual(draft_status(self.dsn,receipt.task_id)["status"],"queued")
        brain=self.finish(json.dumps(VALID))
        self.assertIn("zero-additional-cash",brain.generate.call_args.args[0])
        result=draft_status(self.dsn,receipt.task_id)
        self.assertEqual(result["status"],"quarantined")
        self.assertEqual(result["candidate"]["target"],5)
        self.assertEqual(result["authorized_cents"],0)
        import psycopg
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM business_opportunity").fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT count(*) FROM vault_entry").fetchone()[0],0)

    def test_invalid_model_output_no_candidate(self):
        receipt=self.submit()
        self.finish("I already made a million dollars.")
        self.assertEqual(draft_status(self.dsn,receipt.task_id),
                         {"status":"invalid_draft","candidate":None,"authorized_cents":0})

    def test_replay_reserved_prefix_and_pause(self):
        self.store.set_paused(True)
        self.assertNotEqual(self.submit().status,"accept")
        self.store.set_paused(False)
        receipt=self.submit()
        self.assertTrue(self.submit().replayed)
        self.assertEqual(self.submit(brief="different").status,"idempotency_conflict")
        self.assertEqual(self.submit(reviewer_id=uuid4()).status,"idempotency_conflict")
        for owner in (None,uuid4()):
            self.assertEqual(self.store.submit(owner,DRAFT_PREFIX+"forged","hi").status,"invalid")
        self.assertEqual(self.submit("two").status,"business_draft_busy")
        self.assertEqual(draft_status(self.dsn,receipt.task_id)["status"],"queued")

    def test_parallel_draft_limit_and_rolling_quota(self):
        with ThreadPoolExecutor(max_workers=3) as pool:
            receipts=list(pool.map(lambda key:self.submit(key),["a","b","c"]))
        self.assertEqual(sum(r.status=="accept" for r in receipts),1)
        self.finish(json.dumps(VALID))
        for key in ("d","e"):
            self.assertEqual(self.submit(key).status,"accept")
            self.finish(json.dumps(VALID))
        self.assertEqual(self.submit("f").status,"business_draft_quota")

    def test_stale_fence_does_not_quarantine(self):
        receipt=self.submit()
        claim=self.store.claim()
        self.assertFalse(complete(self.dsn,claim.task_id,uuid4(),success=True,result=json.dumps(VALID)))
        self.assertEqual(draft_status(self.dsn,receipt.task_id)["status"],"running")

    def test_identity_drift_refuses_admission_and_review(self):
        receipt=self.submit()
        self.finish(json.dumps(VALID))
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertEqual(self.submit("drift").status,"denied")
            self.assertIsNone(draft_status(self.dsn,receipt.task_id))
