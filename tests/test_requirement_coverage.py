"""Advisory coverage detects omissions without claiming semantic quality."""
import unittest
from penny.business.requirement_coverage import Requirement, inspect_coverage


class RequirementCoverageTests(unittest.TestCase):
    def test_missing_brand_and_payment(self):
        rules = (Requirement("brand", ("Penny",)),
                 Requirement("payment", ("cash", "credit card")),
                 Requirement("documents", ("passport",)))
        result = inspect_coverage("Pack passport and charger.", rules)
        self.assertEqual([x["status"] for x in result["findings"]],
                         ["not_detected", "not_detected", "literal_match"])
        self.assertFalse(result["semantic_quality_verified"])
        self.assertFalse(result["commercial_release_authorized"])

    def test_token_boundaries_and_negation(self):
        rules = (Requirement("brand", ("Penny",)),)
        self.assertEqual(inspect_coverage("Pennyside", rules)["findings"][0]["status"],
                         "not_detected")
        result = inspect_coverage("Not created by PENNY", rules)
        self.assertEqual(result["findings"][0]["status"], "literal_match")
        self.assertFalse(result["semantic_quality_verified"])

    def test_reject_invalid_definitions(self):
        rule = Requirement("brand", ("Penny",))
        for rules in ((), (rule, rule), (Requirement("brand", ("!!!",)),)):
            with self.assertRaises(ValueError):
                inspect_coverage("Checklist", rules)

    def test_unicode_and_phrase(self):
        rules = (Requirement("payment", ("credit card",)),)
        self.assertEqual(inspect_coverage("ＣＲＥＤＩＴ card", rules)["findings"][0]["status"],
                         "literal_match")
