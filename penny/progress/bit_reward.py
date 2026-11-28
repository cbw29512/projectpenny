"""Private Bit eligibility from the reconciled, reviewed financial read model."""
import logging

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.scheduler.storage_db import locked
from penny.vault.budget import _matched
from .derive import derive
from .state import digest
from .timeline_state import source_digest

logger = logging.getLogger(__name__)
BIT = "bit-v1"
THRESHOLD_CENTS = 50_000


def source_locked(conn, now):
    """Bind the exact fresh reviewed source; never count support or founder income."""
    row = conn.execute("""SELECT version,payload,payload_sha256,generated_at,expires_at
        FROM progress_snapshot ORDER BY version DESC LIMIT 1""").fetchone()
    if not row or not row["generated_at"] <= now < row["expires_at"]:
        return None
    payload = row["payload"]
    if digest(payload) != row["payload_sha256"] or payload["finance"] is None:
        return None
    finance = derive(conn, now, finance=True, business=False)["finance"]
    match = _matched(conn, now)
    if finance is None or finance != payload["finance"] or match is None:
        return None
    net = finance["commercial_receipts"] - finance["commercial_refunds"]
    if net < THRESHOLD_CENTS:
        return None
    return source_digest({"reward": BIT, "threshold_cents": THRESHOLD_CENTS,
                          "metric": "net_commercial_receipts",
                          "version": row["version"], "snapshot": row["payload_sha256"],
                          "reconciliation": str(match["id"])})


def preview(dsn):
    try:
        if not authorize(Actor.ADMIN, Capability.REVIEW_VIRTUAL_WORLD).allowed:
            return None
        with locked(dsn) as (conn, _, now):
            source = source_locked(conn, now)
            return {"eligible": source is not None, "source_digest": source}
    except Exception as exc:
        logger.error("Bit eligibility unavailable (%s)", type(exc).__name__)
        raise
