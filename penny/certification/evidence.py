"""Canonical evidence binding; digests prove integrity, not truthful provenance."""
import hashlib
import json
import logging
import re
from dataclasses import asdict

from penny.brain.identity import IDENTITY_VERSION, SYSTEM_PROMPT
from penny.guardian.policy import identity_matches
from .state import EvidenceRun, ModelManifest, Observation, REPEATS, SUITE_VERSION, MAX_RESPONSE_CHARS
from .suite import CASES

logger = logging.getLogger(__name__)


def digest_json(value):
    wire = json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return hashlib.sha256(wire.encode("utf-8")).hexdigest()


def suite_digest():
    return digest_json({"version":SUITE_VERSION,"repeats":REPEATS,
                        "cases":[asdict(c) for c in CASES]})


def identity_digest():
    return digest_json({"version":IDENTITY_VERSION,"prompt":SYSTEM_PROMPT})


def expected_keys():
    return tuple((c.id,i) for c in CASES for i in range(1,REPEATS+1))


def valid_manifest(model):
    return type(model) is ModelManifest and all(
        type(v) is str and re.fullmatch(r"[a-f0-9]{64}",v) is not None
        for v in (model.model_digest,model.config_digest)
    )


def validate_run(run):
    try:
        if not identity_matches() or type(run) is not EvidenceRun or not valid_manifest(run.model):
            raise ValueError("invalid identity or model manifest")
        if run.identity_digest != identity_digest() or run.suite_digest != suite_digest():
            raise ValueError("identity or suite drift")
        if type(run.observations) is not tuple or len(run.observations) != len(expected_keys()):
            raise ValueError("incomplete evidence")
        keys = []
        for o in run.observations:
            if type(o) is not Observation or type(o.repeat) is not int:
                raise ValueError("invalid observation")
            if (type(o.response) is not str or not 1 <= len(o.response) <= MAX_RESPONSE_CHARS
                    or not o.response.strip() or "\x00" in o.response):
                raise ValueError("invalid response")
            o.response.encode("utf-8")
            keys.append((o.case_id,o.repeat))
        if tuple(keys) != expected_keys():
            raise ValueError("missing, duplicate or reordered observations")
        return digest_json(asdict(run))
    except Exception as exc:
        logger.warning("Certification evidence rejected (%s)",type(exc).__name__)
        raise
