"""Disposable PostgreSQL evidence snapshots, never live or public data."""
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN,DatabaseFixture
from penny.progress.snapshot import preview,record_snapshot,cached
from penny.progress.state import digest
from penny.vault.journal import record
from penny.vault.state import Kind
from penny.vault.reconciliation import reconcile
from penny.business.store import stage
from penny.business.state import Category,Metric,Action
from penny.business.review import advance
from hashlib import sha256


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class SnapshotTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        self.t=int(time.time())-5

    def post(self,kind,cents,ref):
        return record(self.dsn,source_ref=ref,kind=kind,cents=cents,occurred_at=self.t,
                      evidence_ref="secret:"+ref,evidence=b"synthetic",reviewer_id=self.reviewer)

    def match(self,amount):
        return reconcile(self.dsn,source_ref="statement",statement_at=self.t,
                         observed_cash=amount,evidence_ref="secret:statement",
                         evidence=b"synthetic statement",reviewer_id=self.reviewer,
                         coverage_confirmed=True)

    def save(self,ref="snapshot:1",finance=False,business=False,**kw):
        candidate=preview(self.dsn,finance=finance,business=business)
        args=dict(source_ref=ref,expected_digest=candidate["digest"],finance=finance,
                  business=business,reviewer_id=self.reviewer,evidence_ref="secret:review",
                  evidence=b"synthetic disclosure review",confirmed=True)
        return record_snapshot(self.dsn,**(args|kw))

    def test_unavailable_and_default_disclosure_closed(self):
        self.assertEqual(cached(self.dsn),{"status":"unavailable","payload":None})
        self.post(Kind.COMMERCIAL_RECEIPT,100,"sale")
        self.match(100)
        self.assertIsNone(preview(self.dsn)["payload"]["finance"])
        self.save()
        result=cached(self.dsn)
        self.assertEqual(result["status"],"reviewed")
        self.assertIsNone(result["payload"]["finance"])
        self.assertIsNone(result["payload"]["business"])

    def test_financial_separation_and_reconciliation(self):
        for kind,cents,ref in [(Kind.COMMERCIAL_RECEIPT,1000,"sale"),
                              (Kind.COMMERCIAL_REFUND,100,"refund"),
                              (Kind.COMMUNITY_SUPPORT,500,"support"),
                              (Kind.FOUNDER_FUNDING,200,"funding"),
                              (Kind.FOUNDER_PAID_EXPENSE,300,"startup"),
                              (Kind.PAYMENT_FEE,50,"fee"),
                              (Kind.FOUNDER_INCOME,9999,"founder")]:
            self.post(kind,cents,ref)
        self.assertIsNone(preview(self.dsn,finance=True)["payload"]["finance"])
        self.match(1550)
        self.save(finance=True)
        data=cached(self.dsn)["payload"]["finance"]
        self.assertEqual(data["matched_cash"],1550)
        self.assertEqual(data["commercial_result_after_recorded_costs"],550)
        self.assertEqual(data["community_support"],500)
        self.assertNotIn("founder",data)
        self.assertNotIn("secret",str(cached(self.dsn)))

    def test_changed_sources_require_new_review_and_cached_read_no_derive(self):
        old=preview(self.dsn,finance=True)
        self.post(Kind.COMMERCIAL_RECEIPT,100,"sale")
        self.match(100)
        self.assertIsNone(self.save(finance=True,expected_digest=old["digest"]))
        receipt=self.save(finance=True)
        self.assertTrue(self.save(finance=True).replayed)
        with patch("penny.progress.snapshot.derive",side_effect=RuntimeError):
            self.assertEqual(cached(self.dsn)["payload"]["finance"]["matched_cash"],100)
        self.save("snapshot:2")
        self.assertIsNone(cached(self.dsn)["payload"]["finance"])
        self.assertGreater(cached(self.dsn)["version"],1)
        self.assertEqual(self.save(finance=True).entry_id,receipt.entry_id)
        self.assertIsNone(cached(self.dsn)["payload"]["finance"])

    def test_all_experiment_outcomes_and_no_private_titles(self):
        for i,count in enumerate((5,0)):
            evidence=b"synthetic proposal"
            q=stage(self.dsn,source_ref="idea:"+str(i),category=Category.DIGITAL_PRODUCT,
                title="PRIVATE TITLE",hypothesis="PRIVATE DETAILS",metric=Metric.PROTOTYPE_CHECKS_PASSED,
                target=5,duration_seconds=600,additional_cash_cents=0,evidence_ref="secret:proposal",
                evidence=evidence,reviewer_id=self.reviewer,review_until=self.t+3600).entry_id
            for action in (Action.APPROVE,Action.START,Action.MEASURE):
                args={} if action is not Action.MEASURE else dict(observed_at=int(time.time()),measured_count=count)
                self.assertTrue(advance(self.dsn,q,action=action,
                    expected_proposal_sha256=sha256(evidence).hexdigest(),
                    evidence_ref="secret:decision",evidence=b"synthetic decision",
                    reviewer_id=self.reviewer,confirmed=True,**args))
        self.save(business=True)
        data=cached(self.dsn)["payload"]["business"]
        self.assertEqual(data["measured_target_met"],1)
        self.assertEqual(data["measured_target_missed"],1)
        self.assertNotIn("PRIVATE",str(cached(self.dsn)))

    def test_expiry_and_identity_fail_closed(self):
        self.save()
        with patch("penny.progress.snapshot.authorize",return_value=type("D",(),{"allowed":False})()):
            self.assertEqual(cached(self.dsn)["status"],"unavailable")
        with psycopg.connect(self.dsn) as conn:
            # Test clock expiry through a controlled fixture-only timestamp shift.
            conn.execute("ALTER TABLE progress_snapshot DISABLE TRIGGER progress_snapshot_immutable")
            conn.execute("UPDATE progress_snapshot SET generated_at=generated_at-7200,expires_at=expires_at-7200")
            conn.execute("ALTER TABLE progress_snapshot ENABLE TRIGGER progress_snapshot_immutable")
        result=cached(self.dsn)
        self.assertEqual(result["status"],"stale")
        self.assertIsNone(result["payload"])

    def test_private_data_in_corrupt_payload_rejected(self):
        self.save()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("ALTER TABLE progress_snapshot DISABLE TRIGGER progress_snapshot_immutable")
            conn.execute("UPDATE progress_snapshot SET payload=payload || '{\"secret\":\"private\"}'::jsonb")
            conn.execute("ALTER TABLE progress_snapshot ENABLE TRIGGER progress_snapshot_immutable")
        self.assertEqual(cached(self.dsn),{"status":"unavailable","payload":None})
        with self.assertRaises(ValueError):
            digest({"schema":"penny-progress-v1","finance":None,"business":{"private":"text"}})
