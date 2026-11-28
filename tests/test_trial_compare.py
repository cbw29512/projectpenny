"""Private trial comparison fails closed and never certifies improvement."""
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
from penny.business.trial_compare import compare_trials


class TrialCompareTests(unittest.TestCase):
    def test_denied_and_identical_ids(self):
        a, b = uuid4(), uuid4()
        with patch("penny.business.trial_compare.authorize", return_value=SimpleNamespace(allowed=False)):
            self.assertIsNone(compare_trials("unused", a, b))
        with self.assertRaises(ValueError):
            compare_trials("unused", a, a)

    def test_compare_and_unavailable(self):
        a, b = uuid4(), uuid4()

        @contextmanager
        def fake_lock(_):
            yield object(), {}, 100

        def artifact(text):
            return {"status": "private_prototype", "artifact": {
                "content": text, "content_sha256": "a" * 64,
                "format_version": "checklist-text-v1"}}

        old = artifact("Title\n\nRead\n\n[ ] A\n[ ] B\n[ ] C\n")
        new = artifact("Title\n\nRead\n\n[ ] A\n[ ] B\n[ ] D\n")
        with patch("penny.business.trial_compare.authorize", return_value=SimpleNamespace(allowed=True)), \
             patch("penny.business.trial_compare.locked", fake_lock), \
             patch("penny.business.trial_compare._quality", return_value="unreviewed"), \
             patch("penny.business.trial_compare.read_locked", side_effect=[old, new, old, None]):
            result = compare_trials("unused", a, b)
            self.assertEqual(result["comparison"]["added_items"], ["D"])
            self.assertFalse(result["revision_lineage_verified"])
            self.assertFalse(result["improvement_verified"])
            self.assertFalse(result["commercial_release_authorized"])
            unavailable = compare_trials("unused", a, b)
            self.assertEqual(unavailable["status"], "artifacts_unavailable")
            self.assertIsNone(unavailable["comparison"])
            self.assertNotIn("before", unavailable)
