"""Fixed policy vocabulary. Never derive actor identity from model text."""
from dataclasses import dataclass
from enum import Enum


class Actor(Enum):
    WORKER = "worker"
    MODEL = "model"
    MEMBER = "member"
    ADMIN = "administrator"


class Capability(Enum):
    GENERATE_DRAFT = "generate_draft"
    STORE_DRAFT = "store_draft"
    PUBLISH = "publish"
    READ_PRIVATE_MEMORY = "read_private_memory"
    WRITE_MEMORY = "write_memory"
    NETWORK = "network"
    SHELL = "shell"
    SPEND = "spend"
    CHANGE_IDENTITY = "change_identity"
    CHANGE_ENTITLEMENT = "change_entitlement"


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    reason: str
    policy_version: str = "guardian-v0.1"
