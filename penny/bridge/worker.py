"""One bounded communication cycle; deliberately no daemon or auto-start."""
import logging

from .receipts import admit_claim, record_ack
from .release import pending_reply, record_delivery
from .state import BridgeResult
from .worker_state import Cycle
from .worker_store import exclusive_cycle, reserve_action, defer, record_rejection

logger = logging.getLogger(__name__)


def _result(dsn,result,action):
    if type(result) is not BridgeResult:
        defer(dsn,900,block="local_integrity")
        return Cycle("blocked",900)
    if result.status=="backoff":
        delay=max(60,min(result.retry_after,86400))
        defer(dsn,delay)
        return Cycle("backoff",delay)
    if result.status in ("unauthorized","conflict"):
        reason="authentication" if result.status=="unauthorized" else "remote_conflict"
        defer(dsn,900,block=reason)
        return Cycle("blocked",900)
    # Lost claim response: remote may hold a lease, do not claim again yet.
    delay=900 if action=="claim" else 60
    defer(dsn,delay)
    return Cycle("uncertain",delay)


def _cycle(dsn,client):
    action,delay=reserve_action(dsn)
    if action.kind in ("paused","cooldown","waiting"):
        return Cycle(action.kind,delay)
    if action.kind=="claim":
        result=client.claim()
        if type(result) is BridgeResult and result.status=="empty" and result.claim is None:
            return Cycle("empty")
        if type(result) is BridgeResult and result.status=="claimed" and result.claim is not None:
            receipt=admit_claim(dsn,result.claim)
            if receipt.status=="accept":
                return Cycle("admitted")
            # No extra network call or untracked retry. Let the cloud lease expire.
            defer(dsn,900)
            return Cycle("not_admitted",900)
        return _result(dsn,result,"claim")

    approved=None
    if action.kind=="ack":
        result=client.ack(action.question_id,action.fence,action.task_id)
    elif action.kind=="answer":
        approved=pending_reply(dsn,action.question_id)
        if approved is None:
            return Cycle("waiting_review")
        result=client.answer(approved.question_id,approved.fence,approved.text)
    elif action.kind=="reject":
        result=client.reject(action.question_id,action.fence)
    else:
        defer(dsn,900,block="local_integrity")
        return Cycle("blocked",900)
    if type(result) is not BridgeResult or result.status!="ok":
        return _result(dsn,result,action.kind)
    if action.kind=="ack":
        confirmed=record_ack(dsn,action.question_id,action.fence,action.task_id)
    elif action.kind=="answer":
        confirmed=record_delivery(dsn,approved)
    else:
        confirmed=record_rejection(dsn,action)
    if not confirmed:
        defer(dsn,900,block="local_integrity")
        return Cycle("blocked",900)
    return Cycle({"ack":"acknowledged","answer":"delivered","reject":"rejected"}[action.kind])


def run_bridge_once(dsn,client):
    """At most one HTTP operation. Durable state, no tight retries."""
    try:
        with exclusive_cycle(dsn) as acquired:
            if not acquired:
                return Cycle("busy")
            try:
                return _cycle(dsn,client)
            except Exception as exc:
                logger.error("Bridge cycle stopped (%s)",type(exc).__name__)
                # Unknown failure might have committed an external action.
                defer(dsn,900,block="local_integrity")
                return Cycle("blocked",900)
    except Exception as exc:
        logger.error("Bridge unavailable (%s)",type(exc).__name__)
        return Cycle("blocked",900)
