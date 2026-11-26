"""Nonbinding purchase request vocabulary; no execution capability."""
from enum import Enum

class Purpose(Enum):
    COMPUTE="compute"
    HOSTING="hosting"
    SOFTWARE="software"
    BUSINESS_SUPPLIES="business_supplies"

class Rejection(Enum):
    COST="cost"
    RISK="risk"
    INSUFFICIENT_EVIDENCE="insufficient_evidence"
    NOT_NEEDED="not_needed"
    POLICY="policy"

MAX_QUOTE_AGE=604800
