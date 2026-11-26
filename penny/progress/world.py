"""Private append-only virtual world review; no public projection or payments."""
import logging
from uuid import uuid4

from penny.guardian.policy import authorize
from penny.guardian.state import Actor, Capability
from penny.memory.evidence import fingerprint
from penny.memory.review import _valid_id, _valid_ref
from penny.scheduler.storage_db import locked
from penny.vault.state import JournalReceipt
from .world_state import BASELINE, MAX_EVENTS, World, apply, valid_command

logger = logging.getLogger(__name__)


def _load(conn):
    # Deterministic replay, serialized by the existing scheduler transaction.
    rows = conn.execute("SELECT * FROM penny_world_event ORDER BY revision LIMIT %s",
                        (MAX_EVENTS + 1,)).fetchall()
    if len(rows) > MAX_EVENTS:
        raise RuntimeError("world history limit exceeded")
    world = World()
    for row in rows:
        if (row["baseline"] != BASELINE or row["prior_revision"] != world.revision
                or row["revision"] != world.revision + 1):
            raise RuntimeError("world history continuity failure")
        world = apply(world, row["action"], row["asset_id"], row["slot"])
        if world is None:
            raise RuntimeError("invalid stored world transition")
    return world


def inspect(dsn):
    """Private state only; baseline stays provisional and independent of model."""
    try:
        if not authorize(Actor.ADMIN, Capability.REVIEW_VIRTUAL_WORLD).allowed:
            return None
        with locked(dsn) as (conn, _, now):
            world = _load(conn)
            return {"baseline": BASELINE, "revision": world.revision,
                    "owned": sorted(world.owned), "placements": dict(world.placements),
                    "outfit": world.outfit, "status": "private_virtual_only"}
    except Exception as exc:
        logger.error("World state unavailable (%s)", type(exc).__name__)
        raise


def record(dsn, *, source_ref, expected_revision, action, asset_id, slot,
           reviewer_id, evidence_ref, evidence, confirmed):
    """Trusted Maker adapter must verify consent and virtual-only evidence."""
    try:
        decision = authorize(Actor.ADMIN, Capability.REVIEW_VIRTUAL_WORLD)
        if not decision.allowed:
            return None
        if (confirmed is not True or type(expected_revision) is not int
                or not 0 <= expected_revision < MAX_EVENTS
                or not valid_command(action, asset_id, slot)
                or not _valid_id(reviewer_id) or not _valid_ref(source_ref)
                or not _valid_ref(evidence_ref)):
            raise ValueError("invalid virtual world review")
        key = uuid4()
        mark = fingerprint(key, evidence)
        fields = ("prior_revision", "action", "asset_id", "slot", "reviewer_id",
                  "evidence_ref", "evidence_sha256", "evidence_size")
        values = (expected_revision, action, asset_id, slot, reviewer_id,
                  evidence_ref, mark.digest, mark.byte_count)
        with locked(dsn) as (conn, _, now):
            world = _load(conn)  # Refuse corrupt histories, including on replay.
            prior = conn.execute("SELECT * FROM penny_world_event WHERE source_ref=%s",
                                 (source_ref,)).fetchone()
            if prior:
                if tuple(prior[k] for k in fields) != values:
                    raise ValueError("conflicting world review")
                return JournalReceipt(prior["event_id"], True)
            if world.revision != expected_revision:
                return None
            updated = apply(world, action, asset_id, slot)
            if updated is None:
                return None
            conn.execute("""INSERT INTO penny_world_event
                (revision,event_id,source_ref,baseline,prior_revision,action,asset_id,
                 slot,reviewer_id,evidence_ref,evidence_sha256,evidence_size,
                 recorded_at,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (updated.revision, key, source_ref, BASELINE, *values, now,
                 decision.policy_version))
            return JournalReceipt(key)
    except Exception as exc:
        logger.error("World review refused (%s)", type(exc).__name__)
        raise
