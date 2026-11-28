"""Evidence-backed journal, exact replay, balanced postings and separation."""
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN,DatabaseFixture
from penny.vault.state import Kind
from penny.vault.journal import record
from penny.vault.summary import summarize


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class VaultTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        self.occurred=int(time.time())-5

    def post(self,kind,cents,ref,**kw):
        args=dict(source_ref=ref,kind=kind,cents=cents,occurred_at=self.occurred,
                  evidence_ref="private:"+ref,evidence=b"synthetic receipt",reviewer_id=self.reviewer)
        return record(self.dsn,**(args|kw))

    def test_empty_is_unavailable(self):
        result=summarize(self.dsn)
        self.assertEqual(result["status"],"unavailable")
        self.assertIsNone(result["penny"])
        self.assertIsNone(result["founder"])

    def test_separation_and_balanced_postings(self):
        for kind,cents,ref in [
            (Kind.COMMERCIAL_RECEIPT,1000,"sale"),(Kind.COMMERCIAL_REFUND,100,"refund"),
            (Kind.COMMUNITY_SUPPORT,200,"support"),(Kind.FOUNDER_FUNDING,500,"funding"),
            (Kind.OPERATING_EXPENSE,300,"expense"),(Kind.PAYMENT_FEE,50,"fee"),
            (Kind.FOUNDER_PAID_EXPENSE,700,"startup"),(Kind.FOUNDER_INCOME,9000,"merch"),
            (Kind.FOUNDER_EXPENSE,2000,"merch-cost")]:
            self.post(kind,cents,ref)
        result=summarize(self.dsn)
        p=result["penny"]
        self.assertEqual(p["net_commercial_receipts"],900)
        self.assertEqual(p["recorded_cash"],1250)
        self.assertEqual(p["operating_expenses"],1000)
        self.assertEqual(p["commercial_result_after_recorded_costs"],-150)
        self.assertEqual(result["founder"]["recorded_net"],7000)
        with psycopg.connect(self.dsn) as conn:
            rows=conn.execute("SELECT count(*),sum(debit_minor) FROM vault_posting GROUP BY entry_id").fetchall()
            self.assertEqual(rows,[(2,0)]*9)

    def test_concurrent_duplicate_is_idempotent_and_conflict_rejected(self):
        with ThreadPoolExecutor(max_workers=5) as pool:
            receipts=list(pool.map(lambda _:self.post(Kind.COMMERCIAL_RECEIPT,999,"same"),range(7)))
        self.assertEqual(len({r.entry_id for r in receipts}),1)
        self.assertEqual(sum(not r.replayed for r in receipts),1)
        with self.assertRaises(ValueError):
            self.post(Kind.COMMERCIAL_RECEIPT,1000,"same")
        self.assertEqual(summarize(self.dsn)["entry_count"],1)

    def test_reversal_preserves_history_and_cannot_repeat(self):
        original=self.post(Kind.OPERATING_EXPENSE,300,"wrong")
        reversal=self.post(Kind.OPERATING_EXPENSE,300,"reverse",reversal_of=original.entry_id)
        self.assertTrue(self.post(Kind.OPERATING_EXPENSE,300,"reverse",reversal_of=original.entry_id).replayed)
        self.assertEqual(summarize(self.dsn)["penny"]["operating_expenses"],0)
        for target in (original.entry_id,reversal.entry_id):
            with self.assertRaises(ValueError):
                self.post(Kind.OPERATING_EXPENSE,300,"bad",reversal_of=target)
        self.assertEqual(summarize(self.dsn)["entry_count"],2)

    def test_invalid_values_and_identity_drift(self):
        for cents in (0,-1,True,1.25,10**13):
            with self.assertRaises(ValueError):
                self.post(Kind.COMMERCIAL_RECEIPT,cents,"invalid")
        with self.assertRaises(ValueError):
            self.post(Kind.COMMERCIAL_RECEIPT,1,"future",occurred_at=self.occurred+99999)
        with self.assertRaises(ValueError):
            self.post(Kind.COMMERCIAL_RECEIPT,1,"empty",evidence=b"")
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(self.post(Kind.COMMERCIAL_RECEIPT,1,"drift"))
        self.assertEqual(summarize(self.dsn)["entry_count"],0)

    def test_database_refuses_updates_deletes_and_invalid_reversal(self):
        entry=self.post(Kind.COMMERCIAL_RECEIPT,99,"real")
        for query in ("UPDATE vault_entry SET cents=100","DELETE FROM vault_entry"):
            with psycopg.connect(self.dsn) as conn:
                with self.assertRaises(psycopg.errors.RaiseException):
                    conn.execute(query)
                conn.rollback()
        with self.assertRaises(ValueError):
            self.post(Kind.COMMERCIAL_REFUND,99,"bad-reverse",reversal_of=entry.entry_id)
        self.assertEqual(summarize(self.dsn)["penny"]["recorded_cash"],99)

    def test_founder_only_does_not_invent_penny_balance(self):
        self.post(Kind.FOUNDER_INCOME,999,"merch")
        self.assertIsNone(summarize(self.dsn)["penny"])

    def test_actual_costs_can_expose_cash_discrepancy_not_authorize_spend(self):
        self.post(Kind.OPERATING_EXPENSE,100,"historic-cost")
        self.assertTrue(summarize(self.dsn)["penny"]["cash_discrepancy"])
