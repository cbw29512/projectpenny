"""Fixed achievement rules, distinct from the undecided million-dollar metric."""
from enum import Enum

class Achievement(Enum):
    FIRST_DOLLAR="first_dollar"
    IN_THE_GREEN="in_the_green"
    PROOF_OF_CONCEPT="proof_of_concept"

SCHEMA="penny-achievements-v1"
MAX_AGE=3600
