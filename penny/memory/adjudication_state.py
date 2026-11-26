"""Explicit administrator review vocabulary."""
from enum import Enum


class ReviewChoice(str, Enum):
    APPLY = "apply"
    REJECT = "reject"
    ACKNOWLEDGE = "acknowledge"
