"""Typed accounting vocabulary; fixed USD cents, no floating-point money."""
from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class Kind(Enum):
    COMMERCIAL_RECEIPT = "commercial_receipt"
    COMMERCIAL_REFUND = "commercial_refund"
    COMMUNITY_SUPPORT = "community_support"
    FOUNDER_FUNDING = "founder_funding"
    OPERATING_EXPENSE = "operating_expense"
    PAYMENT_FEE = "payment_fee"
    FOUNDER_PAID_EXPENSE = "founder_paid_expense"
    FOUNDER_INCOME = "founder_income"
    FOUNDER_EXPENSE = "founder_expense"


MAX_CENTS = 1_000_000_000_000


@dataclass(frozen=True,slots=True)
class JournalReceipt:
    entry_id: UUID
    replayed: bool = False
