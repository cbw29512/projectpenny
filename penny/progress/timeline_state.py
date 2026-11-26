"""Closed vocabulary for initial business timeline, no arbitrary public text."""
import json
from hashlib import sha256

SCHEMA="penny-timeline-v1"
MAX_EVENTS=20
MAX_TIME=253402300799
LABELS={
    "target_met":"Business experiment met its target.",
    "target_missed":"Business experiment missed its target.",
    "experiment_stopped":"Business experiment was stopped.",
    "experiment_rejected":"Business experiment was not approved.",
    "corrected":"A previously reviewed event was withdrawn.",
}


def source_digest(source):
    # Private integrity binding includes source UUID and evidence digest.
    return sha256(json.dumps(source,sort_keys=True,separators=(",",":"),
        ensure_ascii=True).encode("ascii")).hexdigest()


def public_event(kind,occurred_at):
    if kind not in LABELS or type(occurred_at) is not int or not 0<occurred_at<=MAX_TIME:
        raise ValueError("invalid timeline event")
    # Day precision reduces disclosure of local work patterns.
    return {"kind":kind,"day_epoch":occurred_at//86400*86400}
