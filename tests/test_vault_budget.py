"""Synthetic budget tests: no actual funds or purchases."""
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from uuid import uuid4
from unittest.mock import patch

from database_fixture import DSN,DatabaseFixture
from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.vault.journal import record
from penny.vault.reconciliation import reconcile
from penny.vault.state import Kind
from penny.vault.spend_requests import stage,status,reject
from penny.vault.spend_state import Purpose,Rejection
from penny.vault.budget import review_budget,budget_status
from penny.vault.reservations import reserve,release


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class BudgetTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        self.t=int(time.time())-5
        self.quote=b"synthetic quote"
        self.post("sale",1000)
        self.match=self.reconcile("first",1000)

    def post(self,ref,cents):
        return record(self.dsn,source_ref=ref,kind=Kind.COMMERCIAL_RECEIPT,
                      cents=cents,occurred_at=self.t,evidence_ref=ref,
                      evidence=b"synthetic receipt",reviewer_id=self.reviewer)

    def reconcile(self,ref,cash):
        return reconcile(self.dsn,source_ref=ref,statement_at=self.t,
                         observed_cash=cash,evidence_ref=ref,evidence=b"synthetic statement",
                         reviewer_id=self.reviewer,coverage_confirmed=True).entry_id

    def budget(self,**kw):
        args=dict(reconciliation_id=self.match,ceiling_cents=600,obligations_cents=200,
                  reserve_cents=200,expires_at=self.t+3600,reviewer_id=self.reviewer,
                  evidence_ref="private:review",evidence=b"synthetic budget",confirmed=True)
        return review_budget(self.dsn,**(args|kw))

    def draft(self,cents=400):
        ref=str(uuid4())
        return stage(self.dsn,source_ref=ref,purpose=Purpose.COMPUTE,cents=cents,
                     quote_ref=ref,evidence=self.quote,reviewer_id=self.reviewer,
                     expires_at=self.t+3600).entry_id

    def reserve(self,q,b,cents=400,**kw):
        args=dict(budget_id=b,expected_cents=cents,expected_quote_sha256=sha256(self.quote).hexdigest(),
                  reviewer_id=self.reviewer,confirmed=True)
        return reserve(self.dsn,q,**(args|kw))

    def release(self,q,**kw):
        args=dict(reviewer_id=self.reviewer,evidence_ref="private:cancel",
                  evidence=b"synthetic noncommitment",no_commitment_confirmed=True)
        return release(self.dsn,q,**(args|kw))

    def test_zero_default_and_explicit_ceiling(self):
        self.assertEqual(budget_status(self.dsn)["planning_capacity_cents"],0)
        self.budget(ceiling_cents=0)
        self.assertEqual(budget_status(self.dsn)["planning_capacity_cents"],0)
        self.budget()
        self.assertEqual(budget_status(self.dsn)["planning_capacity_cents"],600)
        for actor in Actor:
            self.assertFalse(authorize(actor,Capability.SPEND).allowed)

    def test_concurrent_holds_do_not_oversubscribe(self):
        b=self.budget()
        qs=[self.draft() for _ in range(3)]
        with ThreadPoolExecutor(max_workers=3) as pool:
            results=list(pool.map(lambda q:self.reserve(q,b),qs))
        self.assertEqual(sum(results),1)
        current=budget_status(self.dsn)
        self.assertEqual(current["reserved_cents"],400)
        self.assertEqual(current["planning_capacity_cents"],200)
        self.assertEqual(current["authorized_cents"],0)

    def test_stale_budget_and_holds_survive_new_review(self):
        b=self.budget()
        q=self.draft()
        self.assertTrue(self.reserve(q,b))
        self.post("another",100)
        self.assertEqual(budget_status(self.dsn)["planning_capacity_cents"],0)
        self.assertEqual(budget_status(self.dsn)["reserved_cents"],400)
        self.assertFalse(self.reserve(self.draft(),b))
        self.match=self.reconcile("second",1100)
        newer=self.budget()
        self.assertNotEqual(newer,b)
        self.assertEqual(budget_status(self.dsn)["planning_capacity_cents"],200)

    def test_exact_quote_and_release_terminal(self):
        b=self.budget()
        q=self.draft()
        self.assertFalse(self.reserve(q,b,cents=399))
        self.assertFalse(self.reserve(q,b,expected_quote_sha256="bad"))
        self.assertTrue(self.reserve(q,b))
        self.assertFalse(self.reserve(q,b))
        self.assertFalse(reject(self.dsn,q,reviewer_id=self.reviewer,reason=Rejection.COST))
        self.assertEqual(status(self.dsn,q)["reserved_cents"],400)
        with self.assertRaises(ValueError):
            self.release(q,no_commitment_confirmed=False)
        self.assertTrue(self.release(q))
        self.assertFalse(self.release(q))
        self.assertFalse(self.reserve(q,b))
        self.assertEqual(status(self.dsn,q)["status"],"released")
        self.assertEqual(budget_status(self.dsn)["planning_capacity_cents"],600)

    def test_invalid_review_and_rejected_quote(self):
        for kw in ({"ceiling_cents":601},{"confirmed":False},{"reserve_cents":True},
                   {"expires_at":self.t+999999},{"reconciliation_id":uuid4()}):
            with self.assertRaises(ValueError):
                self.budget(**kw)
        b=self.budget()
        q=self.draft()
        self.assertTrue(reject(self.dsn,q,reviewer_id=self.reviewer,reason=Rejection.COST))
        self.assertFalse(self.reserve(q,b))
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(self.budget())
            self.assertFalse(self.reserve(q,b))

    def test_superseding_zero_ceiling_keeps_holds(self):
        b=self.budget()
        q=self.draft()
        self.assertTrue(self.reserve(q,b))
        self.budget(ceiling_cents=0)
        self.assertEqual(budget_status(self.dsn)["planning_capacity_cents"],0)
        self.assertEqual(budget_status(self.dsn)["reserved_cents"],400)
        self.assertEqual(status(self.dsn,q)["authorized_cents"],0)
