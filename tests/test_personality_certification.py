"""Synthetic evidence tests; never treat mocked responses as model certification."""
import unittest
from dataclasses import replace
from unittest.mock import Mock, patch
from uuid import uuid4

from penny.certification.capture import capture
from penny.certification.evidence import validate_run, expected_keys
from penny.certification.gate import reviewed_pass, upgrade_eligible
from penny.certification.state import ModelManifest, CaseReview, Review, Verdict, REPEATS
from penny.certification.suite import CASES


class PersonalityCertificationTests(unittest.TestCase):
    def setUp(self):
        self.brain = Mock()
        self.brain.generate.return_value = "Synthetic response for testing only."
        self.model = ModelManifest("a"*64,"b"*64)
        self.run_evidence = capture(self.brain,self.model,worker_isolated=True)

    def review(self,run):
        criteria = {c.id:len(c.criteria) for c in CASES}
        return Review(uuid4(),validate_run(run),tuple(
            CaseReview(key,i,(Verdict.PASS,)*criteria[key],"Synthetic review test")
            for key,i in expected_keys()
        ))

    def test_suite_complete_and_repeated(self):
        self.assertEqual(len(CASES),12)
        self.assertEqual(self.brain.generate.call_count,len(CASES)*REPEATS)
        self.assertEqual(len(set(expected_keys())),len(CASES)*REPEATS)

    def test_capture_requires_isolation_and_valid_manifest(self):
        brain = Mock()
        for model,isolated in ((self.model,False),(ModelManifest("bad","b"*64),True)):
            with self.assertRaises(ValueError):
                capture(brain,model,worker_isolated=isolated)
        brain.generate.assert_not_called()

    def test_capture_stops_on_error(self):
        brain = Mock()
        brain.generate.side_effect = RuntimeError("uncertain inference")
        with self.assertRaises(RuntimeError):
            capture(brain,self.model,worker_isolated=True)
        brain.generate.assert_called_once()

    def test_valid_review_and_upgrade_eligibility(self):
        review = self.review(self.run_evidence)
        candidate = replace(self.run_evidence,model=ModelManifest("c"*64,"b"*64))
        self.assertTrue(reviewed_pass(self.run_evidence,review))
        self.assertTrue(upgrade_eligible(self.run_evidence,review,candidate,self.review(candidate)))
        self.assertFalse(upgrade_eligible(self.run_evidence,review,self.run_evidence,review))

    def test_missing_failed_or_untyped_criteria_denied(self):
        review = self.review(self.run_evidence)
        first = review.cases[0]
        for verdicts in ((),(Verdict.FAIL,)*3,("pass",)*3):
            changed = replace(review,cases=(replace(first,criterion_verdicts=verdicts),)+review.cases[1:])
            self.assertFalse(reviewed_pass(self.run_evidence,changed))
        self.assertFalse(reviewed_pass(self.run_evidence,replace(review,cases=review.cases[:-1])))

    def test_tampered_response_or_model_invalidates_review(self):
        run = self.run_evidence
        review = self.review(run)
        changed = replace(run,observations=(replace(run.observations[0],response="Changed"),)+run.observations[1:])
        self.assertFalse(reviewed_pass(changed,review))
        self.assertFalse(reviewed_pass(replace(run,model=ModelManifest("c"*64,"b"*64)),review))

    def test_incomplete_duplicate_and_suite_drift_denied(self):
        run = self.run_evidence
        review = self.review(run)
        for changed in (replace(run,observations=run.observations[:-1]),
                        replace(run,observations=(run.observations[1],)+run.observations[1:]),
                        replace(run,suite_digest="0"*64)):
            self.assertFalse(reviewed_pass(changed,review))

    def test_guardian_identity_drift_denies_capture_and_review(self):
        review = self.review(self.run_evidence)
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertFalse(reviewed_pass(self.run_evidence,review))
            with self.assertRaises(ValueError):
                capture(self.brain,self.model,worker_isolated=True)
