"""Inactive bounded community worker; at most one claim and one acknowledgment."""
import logging

from penny.bridge.reply_db import reply_call
from penny.bridge.state import BridgeResult
from penny.bridge.worker_state import Cycle
from penny.bridge.worker_store import exclusive_cycle
from penny.guardian.policy import identity_matches
from .scoped import persist_claim
from .transport_state import CommunityClaim

logger = logging.getLogger(__name__)


def run_community_once(dsn, client):
    """Never acknowledge an uncommitted receipt or automatically retry a claim."""
    try:
        if not identity_matches():
            return Cycle("paused",900)
        with exclusive_cycle(dsn) as acquired:
            if not acquired:
                return Cycle("busy",900)
            row=reply_call(dsn,"community_reserve",())
            if not row or row["recorded"] is not True:
                return Cycle("paused",900)
            result=client.community_claim()
            if type(result) is not BridgeResult:
                return Cycle("uncertain",900)
            if result.status=="empty" and result.claim is None:
                return Cycle("empty",900)
            if result.status!="claimed" or type(result.claim) is not CommunityClaim:
                return Cycle("uncertain",900)
            claim=result.claim
            if not persist_claim(dsn,claim):
                return Cycle("not_admitted",900)
            # Separate committed verification; fail closed if mapping or lease changed.
            row=reply_call(dsn,"community_verify",(claim.id,claim.fence))
            if not row or row["recorded"] is not True or not identity_matches():
                return Cycle("receipt_unverified",900)
            ack=client.community_ack(claim.id,claim.fence)
            if type(ack) is BridgeResult and ack.status=="ok" and ack.claim is None:
                recorded=reply_call(dsn,"community_record_ack",(claim.id,claim.fence))
                if recorded and recorded["recorded"] is True:
                    return Cycle("acknowledged",900)
                return Cycle("ack_unrecorded",900)
            # No retry or new claim until durable cooldown; reconciliation is separate.
            return Cycle("ack_uncertain",900)
    except Exception as exc:
        logger.warning("Community cycle stopped (%s)",type(exc).__name__)
        return Cycle("uncertain",900)
