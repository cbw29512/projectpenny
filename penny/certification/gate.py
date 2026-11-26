"""Fail-closed human review gate; never a model self-certification."""
import logging
from uuid import UUID
from .evidence import validate_run, expected_keys
from .state import CaseReview, Review, Verdict
from .suite import CASES

logger = logging.getLogger(__name__)


def reviewed_pass(run,review):
    try:
        digest = validate_run(run)
        if (type(review) is not Review or type(review.reviewer_id) is not UUID
                or review.reviewer_id.int == 0 or review.evidence_digest != digest):
            return False
        if type(review.cases) is not tuple or len(review.cases) != len(expected_keys()):
            return False
        criteria = {c.id:len(c.criteria) for c in CASES}
        keys = []
        for result in review.cases:
            if type(result) is not CaseReview or type(result.repeat) is not int:
                return False
            if result.case_id not in criteria or type(result.criterion_verdicts) is not tuple:
                return False
            if len(result.criterion_verdicts) != criteria[result.case_id]:
                return False
            if any(v is not Verdict.PASS for v in result.criterion_verdicts):
                return False
            if type(result.notes) is not str or not 1 <= len(result.notes.strip()) <= 1000 or "\x00" in result.notes:
                return False
            result.notes.encode("utf-8")
            keys.append((result.case_id,result.repeat))
        return tuple(keys) == expected_keys()
    except Exception as exc:
        logger.warning("Personality review denied (%s)",type(exc).__name__)
        return False


def upgrade_eligible(baseline,baseline_review,candidate,candidate_review):
    """Evidence eligibility only; no runtime change or deployment authorization."""
    try:
        return (reviewed_pass(baseline,baseline_review)
                and reviewed_pass(candidate,candidate_review)
                and baseline.model != candidate.model)
    except Exception as exc:
        logger.warning("Model upgrade eligibility denied (%s)",type(exc).__name__)
        return False
