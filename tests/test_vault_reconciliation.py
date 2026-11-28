"""Synthetic evidence only; verify matching, freshness and immutable history."""
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN, DatabaseFixture
from penny.vault.journal import record
from penny.vault.state import Kind
from penny.vault.reconciliation import reconcile, reconciliation_status, MAX_AGE


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ReconciliationTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        self.t=int(time.time())-5

    def post(self,kind=Kind.COMMERCIAL_RECEIPT,cents=100,ref="sale",**kw):
        args=dict(source_ref=ref,kind=kind,cents=cents,occurred_at=self.t,
                  evidence_ref="private:"+ref,evidence=b"synthetic journal",reviewer_id=self.reviewer)
        return record(self.dsn,**(args|kw))

    def check(self,observed=100,ref="statement",**kw):
        args=dict(source_ref=ref,statement_at=self.t,observed_cash=observed,
                  evidence_ref="private:statement",evidence=b"synthetic statement",
                  reviewer_id=self.reviewer,coverage_confirmed=True)
        return reconcile(self.dsn,**(args|kw))

    def status(self):
        return reconciliation_status(self.dsn)

    def test_unavailable_then_evidenced_zero(self):
        self.assertEqual(self.status()["status"],"unavailable")
        self.assertIsNone(self.status()["recorded_cash"])
        self.check(0)
        self.assertEqual(self.status()["status"],"matched")
        self.assertEqual(self.status()["matched_cash"],0)

    def test_matching_and_mismatching_statement_history(self):
        self.post()
        self.check(99)
        self.assertEqual(self.status()["status"],"mismatch")
        self.assertEqual(self.status()["difference"],-1)
        self.assertIsNone(self.status()["matched_cash"])
        self.check(100,"corrected")
        self.assertEqual(self.status()["matched_cash"],100)
        self.assertEqual(self.status()["difference"],0)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM vault_reconciliation").fetchone()[0],2)

    def test_founder_only_does_not_invalidate_but_penny_event_does(self):
        self.post()
        self.check()
        self.post(Kind.FOUNDER_INCOME,500,"merch")
        self.assertEqual(self.status()["matched_cash"],100)
        # Even a noncash cost invalidates review of the Penny ledger.
        self.post(Kind.FOUNDER_PAID_EXPENSE,10,"cost")
        self.assertEqual(self.status()["status"],"ledger_changed")
        self.assertIsNone(self.status()["matched_cash"])

    def test_reversal_invalidates_even_if_balance_returns(self):
        self.post()
        self.check()
        extra=self.post(Kind.COMMERCIAL_RECEIPT,50,"extra")
        self.post(Kind.COMMERCIAL_RECEIPT,50,"undo",reversal_of=extra.entry_id)
        self.assertEqual(self.status()["recorded_cash"],100)
        self.assertEqual(self.status()["status"],"ledger_changed")

    def test_stale_statement_not_current(self):
        old=self.t-MAX_AGE
        self.post(occurred_at=old)
        self.check(statement_at=old)
        self.assertEqual(self.status()["status"],"stale")
        self.assertIsNone(self.status()["matched_cash"])

    def test_exact_replay_and_older_statement_refusal(self):
        self.post()
        receipt=self.check()
        self.assertEqual(self.check().entry_id,receipt.entry_id)
        self.assertTrue(self.check().replayed)
        with self.assertRaises(ValueError):
            self.check(101)
        with self.assertRaises(ValueError):
            self.check(100,"older",statement_at=self.t-1)
        self.post(Kind.COMMERCIAL_RECEIPT,100,"later",occurred_at=self.t+1)
        self.assertTrue(self.check().replayed)
        with self.assertRaises(ValueError):
            self.check(200,"old-cutoff")

    def test_reject_unconfirmed_invalid_or_identity_drift(self):
        for kw in ({"coverage_confirmed":False},{"observed_cash":True},
                   {"observed_cash":-1},{"statement_at":self.t+99999},{"evidence":b""}):
            args={"observed":0}
            args.update(kw)
            with self.assertRaises(ValueError):
                self.check(**args)
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(self.check(0))
        self.assertEqual(self.status()["status"],"unavailable")

    def test_append_only(self):
        self.check(0)
        for query in ("UPDATE vault_reconciliation SET observed_cash=10",
                      "DELETE FROM vault_reconciliation"):
            with psycopg.connect(self.dsn) as conn:
                with self.assertRaises(psycopg.errors.RaiseException):
                    conn.execute(query)
                conn.rollback()
