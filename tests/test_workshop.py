"""Private printable product generation using real queue and fake inference."""
import json
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from unittest.mock import Mock
from uuid import uuid4

from database_fixture import DSN,DatabaseFixture
from penny.business.store import stage
from penny.business.state import Category,Metric,Action
from penny.business.review import advance
from penny.business.checklist import render_checklist
from penny.business.workshop_admission import submit_prototype
from penny.business.workshop_intake import read_artifact
from penny.scheduler.worker import run_once,WorkerResult
from penny.scheduler.outcomes import complete
from penny.vault.summary import summarize

RAW=json.dumps({"title":"Weekly planning","instructions":"Review each item.",
                "items":["Choose three priorities","Check deadlines","Review completed work"]})


class ChecklistTests(unittest.TestCase):
    def test_printable_shape_and_invalid_inputs(self):
        self.assertEqual(render_checklist(RAW),
            "Weekly planning\n\nReview each item.\n\n[ ] Choose three priorities\n"
            "[ ] Check deadlines\n[ ] Review completed work\n")
        for raw in ('{}','{"title":"a","title":"b"}',json.dumps(
            {"title":"X","instructions":"Y","items":["a","A","b"]}),json.dumps(
            {"title":"X","instructions":"Y","items":["a","b","c"],"tool":"publish"})):
            self.assertIsNone(render_checklist(raw))


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class WorkshopTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        self.evidence=b"synthetic reviewed opportunity"
        self.q=stage(self.dsn,source_ref="workshop-test",category=Category.DIGITAL_PRODUCT,
            title="Weekly planning checklist",hypothesis="A usable checklist",
            metric=Metric.PROTOTYPE_CHECKS_PASSED,target=3,duration_seconds=600,
            additional_cash_cents=0,evidence_ref="private:test",evidence=self.evidence,
            reviewer_id=self.reviewer,review_until=int(time.time())+3600).entry_id

    def step(self,action):
        return advance(self.dsn,self.q,action=action,
            expected_proposal_sha256=sha256(self.evidence).hexdigest(),
            evidence_ref="private:review",evidence=b"synthetic decision",
            reviewer_id=self.reviewer,confirmed=True)

    def start(self):
        self.assertTrue(self.step(Action.APPROVE))
        self.assertTrue(self.step(Action.START))

    def submit(self,key="one"):
        return submit_prototype(self.dsn,self.q,key=key,reviewer_id=self.reviewer)

    def finish(self,raw=RAW):
        brain=Mock()
        brain.generate.return_value=raw
        self.assertEqual(run_once(self.store,brain),WorkerResult.COMPLETED)

    def test_private_printable_product_end_to_end(self):
        self.assertNotEqual(self.submit().status,"accept")
        self.start()
        r=self.submit()
        self.assertEqual(r.status,"accept")
        self.assertTrue(self.submit().replayed)
        self.finish()
        result=read_artifact(self.dsn,r.task_id)
        self.assertEqual(result["status"],"private_prototype")
        self.assertEqual(result["artifact"]["content"],render_checklist(RAW))
        self.assertEqual(summarize(self.dsn)["entry_count"],0)

    def test_invalid_result_no_artifact(self):
        self.start()
        r=self.submit()
        self.finish("I sold a product")
        self.assertEqual(read_artifact(self.dsn,r.task_id),{"status":"not_staged","artifact":None})

    def test_stop_cancels_queued_and_prevents_new_work(self):
        self.start()
        r=self.submit()
        self.assertTrue(self.step(Action.STOP))
        self.assertEqual(read_artifact(self.dsn,r.task_id)["status"],"canceled")
        self.assertIsNone(self.store.claim())
        self.assertNotEqual(self.submit("two").status,"accept")

    def test_running_stop_and_stale_fence(self):
        self.start()
        r=self.submit()
        c=self.store.claim()
        self.assertFalse(complete(self.dsn,c.task_id,uuid4(),success=True,result=RAW))
        self.assertTrue(self.step(Action.STOP))
        self.assertTrue(complete(self.dsn,c.task_id,c.fence,success=True,result=RAW))
        self.assertEqual(read_artifact(self.dsn,r.task_id)["status"],"not_staged")

    def test_concurrent_and_revision_caps(self):
        self.start()
        with ThreadPoolExecutor(max_workers=3) as pool:
            receipts=list(pool.map(self.submit,["a","b","c"]))
        self.assertEqual(sum(r.status=="accept" for r in receipts),1)
        self.finish()
        for key in ("d","e"):
            self.assertEqual(self.submit(key).status,"accept")
            self.finish()
        self.assertEqual(self.submit("f").status,"workshop_quota")

    def test_reserved_prefix_and_integrity_drift(self):
        self.start()
        self.assertEqual(self.store.submit(uuid4(),"workshop:fake","hi").status,"invalid")
        r=self.submit()
        self.finish()
        import psycopg
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE task_outcome SET result='changed' WHERE task_id=%s",(r.task_id,))
        self.assertEqual(read_artifact(self.dsn,r.task_id)["status"],"integrity_error")

    def test_pause_during_generation_preserves_valid_raw_and_explains_missing_artifact(self):
        from penny.runtime.operator_control import stop
        from penny.business.workshop_diagnosis import diagnose
        self.start()
        r=self.submit()
        c=self.store.claim()
        self.assertTrue(stop(self.dsn))
        with self.assertLogs("penny.business.workshop_intake",level="WARNING") as logs:
            self.assertTrue(complete(self.dsn,c.task_id,c.fence,success=True,result=RAW))
        self.assertIn("scheduler paused"," ".join(logs.output))
        self.assertEqual(read_artifact(self.dsn,r.task_id),{"status":"not_staged","artifact":None})
        report=diagnose(self.dsn,r.task_id)
        self.assertTrue(report["current_validator_passed"])
        self.assertGreaterEqual(report["stop_events_in_window"],1)
        self.assertEqual(report["finding"],"valid_output_stop_in_completion_window")
        self.assertFalse(report["cause_certified"])
        self.assertNotIn(RAW,json.dumps(report))
        self.assertIsNone(diagnose(self.dsn,uuid4()))

    def test_diagnosis_distinguishes_invalid_output_and_valid_artifact(self):
        from penny.business.workshop_diagnosis import diagnose
        self.start()
        bad=self.submit("bad")
        self.finish("{}")
        self.assertEqual(diagnose(self.dsn,bad.task_id)["finding"],
                         "stored_output_fails_current_validator")
        good=self.submit("good")
        self.finish()
        self.assertEqual(diagnose(self.dsn,good.task_id)["finding"],
                         "artifact_recorded_integrity_review_separate")
