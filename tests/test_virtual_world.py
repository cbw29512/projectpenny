"""Private virtual inventory persistence; synthetic evidence only."""
import unittest
from unittest.mock import patch
from uuid import uuid4

from database_fixture import DSN, DatabaseFixture
from penny.progress.world import inspect, record
from penny.progress.world_state import World, apply
from penny.scheduler.storage_db import locked


class TransitionTests(unittest.TestCase):
    def test_baseline_cannot_be_replaced_or_modified(self):
        base = World()
        self.assertIsNone(apply(base, "acquire", "new-face", None))
        self.assertIsNone(apply(base, "place", "plant-v1", "left-shelf"))
        self.assertIsNone(apply(base, "acquire", "plant-v1", "left-shelf"))
        self.assertEqual(base.revision, 0)


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class WorldTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer = uuid4()

    def change(self, rev, action, asset, slot=None, **overrides):
        args = dict(source_ref=f"world:{rev}", expected_revision=rev,
                    action=action, asset_id=asset, slot=slot,
                    reviewer_id=self.reviewer, evidence_ref="test:virtual",
                    evidence=b"synthetic virtual change", confirmed=True)
        return record(self.dsn, **(args | overrides))

    def test_persistent_placement_and_wardrobe_replay(self):
        first = self.change(0, "acquire", "plant-v1")
        self.assertTrue(self.change(0, "acquire", "plant-v1").replayed)
        self.assertIsNotNone(first)
        self.assertEqual(inspect(self.dsn)["placements"], {})
        self.assertIsNotNone(self.change(1, "place", "plant-v1", "left-shelf"))
        self.assertIsNotNone(self.change(2, "acquire", "plum-outfit-v1"))
        self.assertIsNone(inspect(self.dsn)["outfit"])
        self.assertIsNotNone(self.change(3, "equip", "plum-outfit-v1", "outfit"))
        old = inspect(self.dsn)
        self.assertIsNotNone(self.change(4, "move", "plant-v1", "right-shelf"))
        new = inspect(self.dsn)
        self.assertEqual(new["outfit"], old["outfit"])
        self.assertEqual(new["owned"], old["owned"])
        self.assertEqual(new["placements"], {"plant-v1": "right-shelf"})
        self.assertEqual(new, inspect(self.dsn))
        self.assertIsNone(self.change(5, "remove", "plant-v1"))
        self.assertIsNotNone(self.change(5, "store", "plant-v1"))
        self.assertIsNotNone(self.change(6, "remove", "plant-v1"))
        self.assertIsNotNone(self.change(7, "unequip", "plum-outfit-v1"))
        self.assertEqual(inspect(self.dsn)["owned"], ["plum-outfit-v1"])

    def test_conflict_unapproved_and_occupied_slot(self):
        with self.assertRaises(ValueError):
            self.change(0, "acquire", "plant-v1", confirmed=False)
        self.assertIsNotNone(self.change(0, "acquire", "plant-v1"))
        with self.assertRaises(ValueError):
            self.change(0, "acquire", "mug-v1")
        self.assertIsNone(self.change(0, "acquire", "mug-v1", source_ref="stale"))
        self.assertIsNotNone(self.change(1, "place", "plant-v1", "left-shelf"))
        self.assertIsNotNone(self.change(2, "acquire", "mug-v1"))
        self.assertIsNone(self.change(3, "place", "mug-v1", "left-shelf"))
        self.assertEqual(inspect(self.dsn)["revision"], 3)
        with patch("penny.brain.identity.SYSTEM_PROMPT", "changed"):
            self.assertIsNone(self.change(3, "store", "plant-v1"))
            self.assertIsNone(inspect(self.dsn))

    def test_history_is_immutable(self):
        self.change(0, "acquire", "plant-v1")
        with self.assertRaises(Exception):
            with locked(self.dsn) as (conn, _, now):
                conn.execute("DELETE FROM penny_world_event")
        self.assertEqual(inspect(self.dsn)["revision"], 1)
