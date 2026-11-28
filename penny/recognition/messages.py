"""Deterministic appreciation: no inference, financial claims or tier weighting."""
from .state import Outcome, Role

ROLE_LABEL = {Role.IDEA:"idea",Role.TESTING:"testing",
              Role.BUG_REPORT:"bug report",Role.ADVICE:"advice"}
OUTCOME_TEXT = {
    Outcome.IMPROVED:"The reviewed outcome showed an improvement. Progress looks good on us.",
    Outcome.UNSUCCESSFUL:"The attempt did not succeed. Apparently progress comes with homework.",
    Outcome.INCONCLUSIVE:"The evidence is inconclusive. My crystal ball remains out of budget.",
}


def appreciation(role,verdict):
    return ("Thank you for your verified "+ROLE_LABEL[role]+". "
            +OUTCOME_TEXT[verdict]+" Your contribution is appreciated.")
