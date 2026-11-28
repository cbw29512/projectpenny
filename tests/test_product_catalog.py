"""Catalog provenance and direct financial attribution, synthetic evidence only."""
import time
import unittest
from hashlib import sha256
from unittest.mock import Mock,patch
from uuid import uuid4

from database_fixture import DSN,DatabaseFixture
from test_workshop import RAW
from penny.business.store import stage
from penny.business.state import Category,Metric,Action
from penny.business.review import advance
from penny.business.workshop_admission import submit_prototype
from penny.business.workshop_intake import read_artifact
from penny.business.quality import review
from penny.business.quality_state import CRITERIA
from penny.business.catalog import register,status,withdraw
from penny.business.product_finance import attribute,summarize_product
from penny.scheduler.worker import run_once,WorkerResult
from penny.vault.journal import record
from penny.vault.state import Kind
from penny.vault.summary import summarize


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class CatalogTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        evidence=b"synthetic proposal"
        self.q=stage(self.dsn,source_ref="catalog:test",category=Category.DIGITAL_PRODUCT,
            title="Checklist",hypothesis="Usable checklist",metric=Metric.PROTOTYPE_CHECKS_PASSED,
            target=3,duration_seconds=600,additional_cash_cents=0,evidence_ref="test:proposal",
            evidence=evidence,reviewer_id=self.reviewer,review_until=int(time.time())+3600).entry_id
        for action in (Action.APPROVE,Action.START):
            self.assertTrue(advance(self.dsn,self.q,action=action,
                expected_proposal_sha256=sha256(evidence).hexdigest(),evidence_ref="test:decision",
                evidence=b"synthetic decision",reviewer_id=self.reviewer,confirmed=True))

    def prototype(self,key):
        task=submit_prototype(self.dsn,self.q,key=key,reviewer_id=self.reviewer).task_id
        brain=Mock()
        brain.generate.return_value=RAW
        self.assertEqual(run_once(self.store,brain),WorkerResult.COMPLETED)
        digest=read_artifact(self.dsn,task)["artifact"]["content_sha256"]
        return task,digest

    def quality(self,task,digest,ref,**kw):
        args=dict(source_ref=ref,expected_content_sha256=digest,checks={k:True for k in CRITERIA},
            revoked=False,reviewer_id=self.reviewer,evidence_ref="test:quality",
            evidence=b"synthetic review",confirmed=True)
        return review(self.dsn,task,**(args|kw)).entry_id

    def register(self,task,digest,review_id,ref="catalog:one",**kw):
        args=dict(source_ref=ref,review_id=review_id,content_sha256=digest,title="Checklist",
            reviewer_id=self.reviewer,evidence_ref="test:catalog",
            evidence=b"synthetic catalog review",confirmed=True)
        return register(self.dsn,task,**(args|kw))

    def product(self,key="one"):
        task,digest=self.prototype(key)
        rid=self.quality(task,digest,"quality:"+key)
        return self.register(task,digest,rid,"catalog:"+key).entry_id

    def post(self,kind,cents,ref,**kw):
        return record(self.dsn,source_ref=ref,kind=kind,cents=cents,occurred_at=int(time.time())-1,
            evidence_ref=ref,evidence=b"synthetic journal",reviewer_id=self.reviewer,**kw).entry_id

    def link(self,p,e,**kw):
        args=dict(reviewer_id=self.reviewer,evidence_ref="test:attribution",
                  evidence=b"synthetic attribution",confirmed=True)
        return attribute(self.dsn,p,e,**(args|kw))

    def test_catalog_requires_latest_review_and_never_authorizes_sale(self):
        task,digest=self.prototype("one")
        self.assertIsNone(self.register(task,digest,uuid4()))
        rid=self.quality(task,digest,"quality:one")
        p=self.register(task,digest,rid)
        self.assertTrue(self.register(task,digest,rid).replayed)
        self.assertIsNone(self.register(task,digest,rid,"catalog:duplicate"))
        self.assertEqual(status(self.dsn,p.entry_id)["status"],"private_candidate")
        self.assertFalse(status(self.dsn,p.entry_id)["commercial_release_authorized"])
        self.quality(task,digest,"quality:two")
        self.assertEqual(status(self.dsn,p.entry_id)["status"],"review_changed")

    def test_withdrawal_preserves_history(self):
        p=self.product()
        self.assertTrue(withdraw(self.dsn,p,reviewer_id=self.reviewer,
            evidence_ref="test:withdraw",evidence=b"synthetic withdrawal",confirmed=True))
        self.assertEqual(status(self.dsn,p)["status"],"withdrawn")
        e=self.post(Kind.COMMERCIAL_REFUND,100,"refund")
        self.assertTrue(self.link(p,e))
        self.assertEqual(summarize_product(self.dsn,p)["result"]["refunds"],100)

    def test_direct_result_and_reversals_without_duplicate_ledger(self):
        p=self.product()
        self.assertIsNone(summarize_product(self.dsn,p)["result"])
        for kind,cents,ref in [(Kind.COMMERCIAL_RECEIPT,1000,"sale"),
                              (Kind.COMMERCIAL_REFUND,100,"refund"),
                              (Kind.PAYMENT_FEE,50,"fee"),
                              (Kind.FOUNDER_PAID_EXPENSE,200,"cost")]:
            e=self.post(kind,cents,ref)
            self.assertTrue(self.link(p,e))
            self.assertTrue(self.link(p,e))
        self.assertEqual(summarize_product(self.dsn,p)["result"]["recorded_direct_result"],650)
        original=self.post(Kind.OPERATING_EXPENSE,300,"wrong")
        self.assertTrue(self.link(p,original))
        reverse=self.post(Kind.OPERATING_EXPENSE,300,"undo",reversal_of=original)
        self.assertFalse(self.link(p,reverse))
        self.assertEqual(summarize_product(self.dsn,p)["result"]["recorded_direct_result"],650)
        self.assertEqual(summarize(self.dsn)["entry_count"],6)

    def test_no_double_attribution_or_support_as_sales(self):
        a,b=self.product("one"),self.product("two")
        e=self.post(Kind.COMMERCIAL_RECEIPT,100,"sale")
        self.assertTrue(self.link(a,e))
        with self.assertRaises(ValueError):
            self.link(b,e)
        for kind in (Kind.COMMUNITY_SUPPORT,Kind.FOUNDER_FUNDING,Kind.FOUNDER_INCOME):
            self.assertFalse(self.link(a,self.post(kind,99,kind.value)))
        self.assertIsNone(summarize_product(self.dsn,b)["result"])

    def test_conflicting_review_and_identity_drift(self):
        task,digest=self.prototype("one")
        rid=self.quality(task,digest,"quality:one")
        p=self.register(task,digest,rid).entry_id
        with self.assertRaises(ValueError):
            self.register(task,digest,rid,title="Different")
        e=self.post(Kind.COMMERCIAL_RECEIPT,100,"sale")
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(status(self.dsn,p))
            self.assertFalse(self.link(p,e))
