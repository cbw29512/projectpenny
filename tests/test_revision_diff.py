"""Exact checklist change detection, not an automated quality score."""
import unittest
from penny.business.revision_compare import _compare


class RevisionDiffTests(unittest.TestCase):
    def test_add_remove_reorder_and_title(self):
        old="Old\n\nInstructions\n\n[ ] A\n[ ] B\n[ ] C\n"
        new="New\n\nInstructions\n\n[ ] B\n[ ] D\n[ ] A\n"
        result=_compare(old,new)
        self.assertEqual(result["added_items"],["D"])
        self.assertEqual(result["removed_items"],["C"])
        self.assertEqual(result["retained_items"],["A","B"])
        self.assertTrue(result["retained_order_changed"])
        self.assertTrue(result["title_changed"])
        self.assertFalse(result["instructions_changed"])

    def test_unchanged_and_unicode_line_separator(self):
        content="Title\n\nRead\n\n[ ] A\u2028B\n[ ] C\n[ ] D\n"
        result=_compare(content,content)
        self.assertFalse(result["content_changed"])
        self.assertEqual(result["retained_items"],["A\u2028B","C","D"])
        self.assertEqual(result["added_items"],[])
        self.assertEqual(result["removed_items"],[])
