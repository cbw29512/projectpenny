"""Bounded, untrusted model output; never a reviewed opportunity."""
from dataclasses import dataclass
from .state import Category, Metric

DRAFT_PREFIX="business-draft:"
DAILY_LIMIT=3

@dataclass(frozen=True, slots=True)
class Draft:
    category: Category
    title: str
    hypothesis: str
    metric: Metric
    target: int
    duration_seconds: int
    additional_cash_cents: int=0
