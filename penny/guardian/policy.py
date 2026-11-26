"""Deny by default. No authorization from natural-language instructions."""
import hashlib
import hmac
import logging

from penny.brain import identity
from .state import Actor, Capability, Decision

logger = logging.getLogger(__name__)
APPROVED_IDENTITY_VERSION = "penny-v0.1"
APPROVED_PROMPT_SHA256 = "75a9b0bb59b89daa6921b7794a364adb3c85849f2d1e8382acdf1dfdd4af9372"
_ALLOWED = frozenset({
    (Actor.WORKER, Capability.GENERATE_DRAFT),
    (Actor.WORKER, Capability.STORE_DRAFT),
    (Actor.WORKER, Capability.STAGE_MEMORY_CANDIDATE),
    (Actor.ADMIN, Capability.APPROVE_BUSINESS_MEMORY),
    (Actor.ADMIN, Capability.REVOKE_BUSINESS_MEMORY),
    (Actor.WORKER, Capability.RECALL_BUSINESS_MEMORY),
    (Actor.WORKER, Capability.STAGE_MEMORY_MAINTENANCE),
    (Actor.ADMIN, Capability.REVIEW_MEMORY_MAINTENANCE),
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
        if not identity_matches():
            return Decision(False, "identity_mismatch")
        if (actor, capability) not in _ALLOWED:
            return Decision(False, "capability_denied")
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
