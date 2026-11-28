"""Bit's milestone uses real disposable DB and synthetic reviewed ledger entries."""
import time
import unittest
from uuid import uuid4
from unittest.mock import patch
from database_fixture import DSN, DatabaseFixture
from penny.progress.bit_reward import preview
from penny.progress.world import record, browser_candidate
from penny.progress.world_state import World, apply
from penny.progress.snapshot import preview as snapshot_preview, record_snapshot
from penny.vault.journal import record as post
from penny.vault.reconciliation import reconcile
from penny.vault.state import Kind


class BitTransitionTests(unittest.TestCase):
    def test_dedicated_slot_and_no_replacement(self):
        acquired = apply(World(), "acquire", "bit-v1", None)
        self.assertIsNone(apply(acquired, "place", "bit-v1", "desk-corner"))
        self.assertIsNone(apply(acquired, "acquire", "bit-v1", None))
        placed = apply(acquired, "place", "bit-v1", "bit-dock")
        self.assertEqual(dict(placed.placements), {"bit-v1":"bit-dock"})
        self.assertIsNone(apply(placed, "remove", "bit-v1", None))
        self.assertIsNone(apply(placed, "place", "mug-v1", "bit-dock"))


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class BitRewardTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer = uuid4()
        self.t = int(time.time())-5

    def entry(self, kind, cents, ref):
        return post(self.dsn,source_ref=ref,kind=kind,cents=cents,occurred_at=self.t,
                    evidence_ref="private:"+ref,evidence=b"synthetic",reviewer_id=self.reviewer)

    def finance(self,cash,ref):
        reconcile(self.dsn,source_ref="statement:"+ref,statement_at=self.t,
                  observed_cash=cash,evidence_ref="private:statement",evidence=b"synthetic",
                  reviewer_id=self.reviewer,coverage_confirmed=True)
        p=snapshot_preview(self.dsn,finance=True)
        record_snapshot(self.dsn,source_ref="snapshot:"+ref,expected_digest=p["digest"],
                        finance=True,business=False,reviewer_id=self.reviewer,
                        evidence_ref="private:review",evidence=b"synthetic",confirmed=True)

    def change(self,revision,action,slot=None,**kw):
        args=dict(source_ref=f"bit:{revision}",expected_revision=revision,action=action,
                  asset_id="bit-v1",slot=slot,reviewer_id=self.reviewer,
                  evidence_ref="private:bit",evidence=b"synthetic",confirmed=True)
        return record(self.dsn,**(args|kw))

    def test_support_and_49999_never_unlock(self):
        self.entry(Kind.COMMUNITY_SUPPORT,100_000,"support")
        self.entry(Kind.FOUNDER_FUNDING,50_000,"funding")
        self.entry(Kind.COMMERCIAL_RECEIPT,49_999,"sale")
        self.finance(199_999,"one")
        self.assertFalse(preview(self.dsn)["eligible"])
        self.assertIsNone(self.change(0,"acquire",reward_source="0"*64))
        self.assertEqual(browser_candidate(self.dsn)["placements"],{})

    def test_exact_gate_and_persistence(self):
        self.entry(Kind.COMMERCIAL_RECEIPT,50_000,"sale")
        self.finance(50_000,"one")
        source=preview(self.dsn)["source_digest"]
        self.assertTrue(source)
        self.assertIsNone(self.change(0,"acquire"))
        self.assertIsNone(self.change(0,"acquire",reward_source="0"*64))
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(self.change(0,"acquire",reward_source=source))
        self.assertIsNotNone(self.change(0,"acquire",reward_source=source))
        self.assertTrue(self.change(0,"acquire",reward_source=source).replayed)
        self.assertIsNotNone(self.change(1,"place","bit-dock"))
        self.entry(Kind.COMMERCIAL_REFUND,1,"refund")
        self.assertFalse(preview(self.dsn)["eligible"])
        self.assertEqual(browser_candidate(self.dsn)["placements"],{"bit-v1":"bit-dock"})
        self.assertEqual(browser_candidate(self.dsn)["revision"],2)
        self.assertIsNotNone(self.change(2,"store"))
        self.assertEqual(browser_candidate(self.dsn)["placements"],{})

    def test_refund_before_approval_invalidates_old_binding(self):
        self.entry(Kind.COMMERCIAL_RECEIPT,50_000,"sale")
        self.finance(50_000,"one")
        source=preview(self.dsn)["source_digest"]
        self.entry(Kind.COMMERCIAL_REFUND,1,"refund")
        self.assertIsNone(self.change(0,"acquire",reward_source=source))
        self.assertEqual(browser_candidate(self.dsn)["revision"],0)
