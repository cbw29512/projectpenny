"""Kiosk projection excludes member content and raw internal drafts."""
import unittest
from uuid import uuid4

import psycopg

from database_fixture import DSN, DatabaseFixture


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class KioskSnapshotTests(DatabaseFixture):
    def read(self):
        with psycopg.connect(self.dsn) as conn:
            return conn.execute("SELECT snapshot FROM kiosk_snapshot").fetchone()[0]

    def test_initial_state(self):
        s = self.read()
        self.assertFalse(s["enabled"])
        self.assertIsNone(s["active"])
        self.assertEqual(s["recent"], [])
        self.assertFalse(s["visitor_busy"])

    def test_member_payload_and_raw_result_never_projected(self):
        with psycopg.connect(self.dsn) as conn:
            task = uuid4()
            conn.execute("""INSERT INTO work_task
                (id,member_id,tier_snapshot,idempotency_key,payload,submitted_at,deadline,state)
                VALUES (%s,%s,0,'visitor','PRIVATE_VISITOR_TEXT',1,9999999999,'succeeded')""",
                (task,uuid4()))
            conn.execute("INSERT INTO task_outcome VALUES (%s,'succeeded','PRIVATE_VISITOR_RESULT',2,1)", (task,))
            internal = uuid4()
            conn.execute("""INSERT INTO work_task
                (id,idempotency_key,payload,submitted_at,deadline,state)
                VALUES (%s,'internal','PRIVATE_PROMPT',1,9999999999,'succeeded')""", (internal,))
            conn.execute("INSERT INTO task_outcome VALUES (%s,'succeeded','RAW_INTERNAL_RESULT',2,1)", (internal,))
        s = self.read()
        self.assertEqual(s["counts"], {"succeeded":1})
        self.assertEqual(s["recent"], [])
        for secret in ("PRIVATE_VISITOR_TEXT","PRIVATE_VISITOR_RESULT","PRIVATE_PROMPT","RAW_INTERNAL_RESULT"):
            self.assertNotIn(secret,str(s))

    def test_running_internal_task_only_safe_metadata(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute("""INSERT INTO work_task
                (id,idempotency_key,payload,submitted_at,deadline,state,fence,started_at,lease_until)
                VALUES (%s,'internal','PRIVATE_PROMPT',1,9999999999,'running',%s,2,9999999999)""",
                (uuid4(),uuid4()))
        s = self.read()
        self.assertEqual(s["active"]["kind"],"internal task")
        self.assertNotIn("PRIVATE_PROMPT",str(s))
        self.assertNotIn("fence",s["active"])

    def test_measured_experiment_is_distinct_from_task_success(self):
        import time
        from hashlib import sha256
        from penny.business.store import stage
        from penny.business.state import Category, Metric, Action
        from penny.business.review import advance
        reviewer = uuid4()
        evidence = b"synthetic test observation"
        q = stage(self.dsn, source_ref="kiosk-measurement", category=Category.DIGITAL_PRODUCT,
                  title="Private checklist", hypothesis="Five checks", metric=Metric.PROTOTYPE_CHECKS_PASSED,
                  target=5, duration_seconds=600, additional_cash_cents=0,
                  evidence_ref="private:test", evidence=evidence,
                  reviewer_id=reviewer, review_until=int(time.time())+3600).entry_id
        args = dict(expected_proposal_sha256=sha256(evidence).hexdigest(),
                    evidence_ref="private:test", evidence=evidence, reviewer_id=reviewer, confirmed=True)
        self.assertIsNone(self.read()["latest_measurement"])
        for action in (Action.APPROVE, Action.START):
            self.assertTrue(advance(self.dsn,q,action=action,**args))
        self.assertIsNone(self.read()["latest_measurement"])
        self.assertTrue(advance(self.dsn,q,action=Action.MEASURE,observed_at=int(time.time()),
                                measured_count=3,**args))
        m = self.read()["latest_measurement"]
        self.assertEqual((m["measured_count"],m["target"]),(3,5))
        self.assertNotIn("evidence_ref",m)
        self.assertNotIn("reviewer_id",m)

    def test_finance_matches_vault_and_excludes_founder(self):
        import time
        from penny.vault.journal import record
        from penny.vault.state import Kind
        from penny.vault.summary import summarize
        self.assertIsNone(self.read()["finance"])
        reviewer=uuid4()
        for kind,cents in ((Kind.FOUNDER_INCOME,9000),(Kind.COMMERCIAL_RECEIPT,1000),
                           (Kind.COMMERCIAL_REFUND,100),(Kind.OPERATING_EXPENSE,200),
                           (Kind.PAYMENT_FEE,50),(Kind.COMMUNITY_SUPPORT,300)):
            record(self.dsn,source_ref="kiosk-"+kind.value,kind=kind,cents=cents,
                   occurred_at=int(time.time())-1,evidence_ref="private:kiosk",
                   evidence=b"synthetic test only",reviewer_id=reviewer)
            if kind is Kind.FOUNDER_INCOME:
                self.assertIsNone(self.read()["finance"])
        finance=self.read()["finance"]
        p=summarize(self.dsn)["penny"]
        self.assertEqual(finance,{"net_receipts":p["net_commercial_receipts"],
            "expenses":p["operating_expenses"]+p["payment_fees"],
            "recorded_cash":p["recorded_cash"],"community_support":p["community_support"],
            "status":"recorded_unreconciled"})
        self.assertNotIn("private:kiosk",str(self.read()))
