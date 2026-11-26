import unittest
from unittest.mock import patch

from penny.guardian.policy import authorize, identity_matches, validate_draft
from penny.guardian.state import Actor, Capability


class GuardianTests(unittest.TestCase):
    def test_canonical_identity(self):
        self.assertTrue(identity_matches())

    def test_allowlist_exhaustive(self):
        for actor in Actor:
            for capability in Capability:
                with self.subTest(actor=actor, capability=capability):
                    allowed = (actor is Actor.WORKER and capability in (
                        Capability.GENERATE_DRAFT, Capability.STORE_DRAFT,
                        Capability.READ_APPROVED_BRIDGE_REPLY,
                        Capability.STAGE_MEMORY_CANDIDATE, Capability.RECALL_BUSINESS_MEMORY,
                        Capability.STAGE_MEMORY_MAINTENANCE, Capability.RECALL_MEMBER_MEMORY,
                    )) or (actor is Actor.ADMIN and capability in (
                        Capability.APPROVE_BUSINESS_MEMORY, Capability.REVOKE_BUSINESS_MEMORY,
                        Capability.REVIEW_MEMORY_MAINTENANCE, Capability.PURGE_EXPIRED_MEMORY_DRAFTS,
                        Capability.ISSUE_MEMBER_SESSION, Capability.VERIFY_CONTRIBUTION,
                        Capability.APPROVE_BRIDGE_REPLY, Capability.RECORD_VAULT_ENTRY,
                        Capability.RECONCILE_VAULT, Capability.REVIEW_SPEND_REQUEST,
                        Capability.REVIEW_VAULT_BUDGET, Capability.RESERVE_VAULT_FUNDS,
                    ))
                    allowed = allowed or (actor is Actor.MEMBER and capability in (
                        Capability.MANAGE_OWN_MEMORY, Capability.WITHDRAW_MEMORY_CONSENT,
                        Capability.MANAGE_OWN_RECOGNITION, Capability.WITHDRAW_RECOGNITION,
                    ))
                    self.assertEqual(authorize(actor, capability).allowed, allowed)

    def test_untrusted_strings_and_unknown_values(self):
        for actor, capability in [
            ("worker", Capability.GENERATE_DRAFT),
            (Actor.WORKER, "generate_draft"),
            (None, None),
            ([], {}),
        ]:
            self.assertFalse(authorize(actor, capability).allowed)

    def test_prompt_drift_blocks_generation_and_storage(self):
        with patch("penny.brain.identity.SYSTEM_PROMPT", "changed"):
            self.assertFalse(identity_matches())
            self.assertFalse(authorize(Actor.WORKER, Capability.GENERATE_DRAFT).allowed)
            self.assertFalse(validate_draft("draft").allowed)

    def test_version_drift(self):
        with patch("penny.brain.identity.IDENTITY_VERSION", "unapproved"):
            self.assertFalse(identity_matches())

    def test_draft_limits(self):
        for text in (None, {}, "", " ", "x" * 16001, "x\x00y"):
            self.assertFalse(validate_draft(text).allowed)
        self.assertTrue(validate_draft("Penny's private draft").allowed)

    def test_internal_policy_exception_fails_closed(self):
        with patch("penny.guardian.policy.identity_matches", side_effect=RuntimeError):
            self.assertFalse(authorize(Actor.WORKER, Capability.STORE_DRAFT).allowed)
