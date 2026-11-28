"""Immutable domain state. All priority inputs come from trusted adapters."""

from dataclasses import dataclass
from enum import Enum, IntEnum


class Tier(IntEnum):
    FREE = 0
    COPPER = 1
    BRONZE = 2
    SILVER = 3
    GOLD = 4
    PLATINUM = 5
    INNER_CIRCLE = 6


class QueueClass(str, Enum):
    BUSINESS = "business"
    SUPPORTER = "supporter"
    FREE = "free"


class Admission(str, Enum):
    ACCEPT = "accept"
    INVALID = "invalid"
    PAUSED = "paused"
    EXPIRED = "expired"
    DUPLICATE_ID = "duplicate_id"
    FULL = "full"
    MEMBER_LIMIT = "member_limit"


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    member_id: str | None
    tier: Tier | None
    submitted_at: int
    expires_at: int

    @property
    def queue_class(self) -> QueueClass:
        # Internal business work is distinct from paid public work.
        if self.member_id is None:
            return QueueClass.BUSINESS
        return QueueClass.FREE if self.tier == Tier.FREE else QueueClass.SUPPORTER

    def valid(self) -> bool:
        return (
            isinstance(self.task_id, str) and bool(self.task_id.strip())
            and type(self.submitted_at) is int
            and type(self.expires_at) is int
            and 0 <= self.submitted_at < self.expires_at
            and (
                (self.member_id is None and self.tier is None)
                or (
                    isinstance(self.member_id, str)
                    and bool(self.member_id.strip())
                    and isinstance(self.tier, Tier)
                )
            )
        )


@dataclass(frozen=True, slots=True)
class QueueSnapshot:
    active: TaskSpec | None = None
    waiting: tuple[TaskSpec, ...] = ()
    paused: bool = False
    last_member_id: str | None = None
    # Rolling actual compute usage, supplied by the eventual durable adapter.
    business_seconds: int = 0
    supporter_seconds: int = 0
    free_seconds: int = 0

    def usage(self, queue_class: QueueClass) -> int:
        return {
            QueueClass.BUSINESS: self.business_seconds,
            QueueClass.SUPPORTER: self.supporter_seconds,
            QueueClass.FREE: self.free_seconds,
        }[queue_class]
