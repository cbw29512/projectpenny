"""Deny by default. No authorization from natural-language instructions."""
import hashlib
import hmac
import logging

from penny.brain import identity
from .state import Actor, Capability, Decision

logger = logging.getLogger(__name__)
APPROVED_IDENTITY_VERSION = "penny-v0.2"
APPROVED_PROMPT_SHA256 = "e1ef18151ddd473f2d73756204740a97e28c5cd254c0b46a500196f069a08e9a"
_ALLOWED = frozenset({
    (Actor.WORKER, Capability.GENERATE_DRAFT),
    (Actor.WORKER, Capability.STORE_DRAFT),
    (Actor.WORKER, Capability.STAGE_MEMORY_CANDIDATE),
    (Actor.ADMIN, Capability.APPROVE_BUSINESS_MEMORY),
    (Actor.ADMIN, Capability.REVOKE_BUSINESS_MEMORY),
    (Actor.WORKER, Capability.RECALL_BUSINESS_MEMORY),
    (Actor.WORKER, Capability.STAGE_MEMORY_MAINTENANCE),
    (Actor.ADMIN, Capability.REVIEW_MEMORY_MAINTENANCE),
    (Actor.ADMIN, Capability.PURGE_EXPIRED_MEMORY_DRAFTS),
    (Actor.MEMBER, Capability.MANAGE_OWN_MEMORY),
    (Actor.MEMBER, Capability.WITHDRAW_MEMORY_CONSENT),
    (Actor.ADMIN, Capability.ISSUE_MEMBER_SESSION),
    (Actor.WORKER, Capability.RECALL_MEMBER_MEMORY),
    (Actor.ADMIN, Capability.VERIFY_CONTRIBUTION),
    (Actor.MEMBER, Capability.MANAGE_OWN_RECOGNITION),
    (Actor.MEMBER, Capability.WITHDRAW_RECOGNITION),
})


def identity_matches() -> bool:
    try:
        if identity.IDENTITY_VERSION != APPROVED_IDENTITY_VERSION:
            return False
        digest = hashlib.sha256(identity.SYSTEM_PROMPT.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, APPROVED_PROMPT_SHA256)
    except Exception:
        logger.error("Guardian identity integrity check failed")
        return False


def authorize(actor: Actor, capability: Capability) -> Decision:
    try:
        if type(actor) is not Actor or type(capability) is not Capability:
            return Decision(False, "invalid_policy_input")
        # Privacy withdrawal must remain available even during identity failure.
        if actor is Actor.MEMBER and capability in (
            Capability.WITHDRAW_MEMORY_CONSENT,Capability.WITHDRAW_RECOGNITION):
            return Decision(True, "authenticated_owner_privacy_only")
        if not identity_matches():
            return Decision(False, "identity_mismatch")
        if (actor, capability) not in _ALLOWED:
            return Decision(False, "capability_denied")
        if capability is Capability.VERIFY_CONTRIBUTION:
            return Decision(True, "administrator_evidence_review_only")
        if capability is Capability.MANAGE_OWN_RECOGNITION:
            return Decision(True, "authenticated_owner_recognition_only")
        if capability is Capability.RECALL_MEMBER_MEMORY:
            return Decision(True, "fenced_owner_consent_recall_only")
        if capability is Capability.ISSUE_MEMBER_SESSION:
            return Decision(True, "trusted_identity_adapter_only")
        if capability is Capability.MANAGE_OWN_MEMORY:
            return Decision(True, "authenticated_owner_memory_only")
        if capability is Capability.PURGE_EXPIRED_MEMORY_DRAFTS:
            return Decision(True, "administrator_expired_draft_purge_only")
        if capability is Capability.REVIEW_MEMORY_MAINTENANCE:
            return Decision(True, "administrator_maintenance_review_only")
        if capability is Capability.STAGE_MEMORY_MAINTENANCE:
            return Decision(True, "quarantined_maintenance_only")
        if capability is Capability.STAGE_MEMORY_CANDIDATE:
            return Decision(True, "quarantined_candidate_only")
        if capability in (Capability.APPROVE_BUSINESS_MEMORY, Capability.REVOKE_BUSINESS_MEMORY):
            return Decision(True, "administrator_memory_review_only")
        if capability is Capability.RECALL_BUSINESS_MEMORY:
            return Decision(True, "fenced_internal_recall_only")
        return Decision(True, "private_draft_only")
    except Exception:
        logger.error("Guardian authorization failed closed")
        return Decision(False, "policy_error")


def validate_draft(text: object) -> Decision:
    # Shape validation only. Natural-language factual and behavioral review
    # must occur before a future public release, not by guessing from keywords.
    try:
        decision = authorize(Actor.WORKER, Capability.STORE_DRAFT)
        if not decision.allowed:
            return decision
        if type(text) is not str or not text.strip() or len(text) > 16000 or "\x00" in text:
            return Decision(False, "invalid_draft")
        return decision
    except Exception:
        logger.error("Guardian draft validation failed closed")
        return Decision(False, "policy_error")
