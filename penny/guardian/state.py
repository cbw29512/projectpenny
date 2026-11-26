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
    APPROVE_BRIDGE_REPLY = "approve_bridge_reply"
    READ_APPROVED_BRIDGE_REPLY = "read_approved_bridge_reply"
    PUBLISH = "publish"
    READ_PRIVATE_MEMORY = "read_private_memory"
    WRITE_MEMORY = "write_memory"
    STAGE_MEMORY_CANDIDATE = "stage_memory_candidate"
    APPROVE_BUSINESS_MEMORY = "approve_business_memory"
    REVOKE_BUSINESS_MEMORY = "revoke_business_memory"
    RECALL_BUSINESS_MEMORY = "recall_business_memory"
    STAGE_MEMORY_MAINTENANCE = "stage_memory_maintenance"
    REVIEW_MEMORY_MAINTENANCE = "review_memory_maintenance"
    PURGE_EXPIRED_MEMORY_DRAFTS = "purge_expired_memory_drafts"
    MANAGE_OWN_MEMORY = "manage_own_memory"
    WITHDRAW_MEMORY_CONSENT = "withdraw_memory_consent"
    ISSUE_MEMBER_SESSION = "issue_member_session"
    RECALL_MEMBER_MEMORY = "recall_member_memory"
    VERIFY_CONTRIBUTION = "verify_contribution"
    MANAGE_OWN_RECOGNITION = "manage_own_recognition"
    WITHDRAW_RECOGNITION = "withdraw_recognition"
    NETWORK = "network"
    SHELL = "shell"
    RECORD_VAULT_ENTRY = "record_vault_entry"
    RECONCILE_VAULT = "reconcile_vault"
    REVIEW_SPEND_REQUEST = "review_spend_request"
    REVIEW_VAULT_BUDGET = "review_vault_budget"
    RESERVE_VAULT_FUNDS = "reserve_vault_funds"
    REVIEW_BUSINESS_EXPERIMENT = "review_business_experiment"
    REQUEST_BUSINESS_DRAFT = "request_business_draft"
    STAGE_BUSINESS_DRAFT = "stage_business_draft"
    SPEND = "spend"
    CHANGE_IDENTITY = "change_identity"
    CHANGE_ENTITLEMENT = "change_entitlement"


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    reason: str
    policy_version: str = "guardian-v0.18"
