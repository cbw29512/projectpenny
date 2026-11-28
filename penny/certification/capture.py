"""Offline evidence capture; never run alongside the production worker."""
import logging
from .evidence import identity_digest, suite_digest, valid_manifest, validate_run
from .state import EvidenceRun, Observation, REPEATS
from .suite import CASES
from penny.guardian.policy import identity_matches

logger = logging.getLogger(__name__)


def capture(brain, model, *, worker_isolated, timeout=90):
    """Trusted operator must confirm exclusive inference and exact model manifest.

    No automatic retry after uncertain inference. Never submits queue jobs,
    modifies identity, or activates a model. Caller must preserve evidence.
    """
    try:
        if worker_isolated is not True or not identity_matches() or not valid_manifest(model):
            raise ValueError("offline certification preconditions unmet")
        if type(timeout) not in (int,float) or not 0 < timeout <= 90:
            raise ValueError("invalid per-case timeout")
        observations = []
        for case in CASES:
            for repeat in range(1,REPEATS+1):
                response = brain.generate(case.prompt,timeout)
                # Stop immediately on malformed output, rather than spend more compute.
                if type(response) is not str or not response.strip() or len(response)>16000 or "\x00" in response:
                    raise ValueError("invalid certification output")
                response.encode("utf-8")
                observations.append(Observation(case.id,repeat,response))
        run = EvidenceRun(model,identity_digest(),suite_digest(),tuple(observations))
        validate_run(run)
        return run
    except Exception as exc:
        logger.error("Offline personality capture stopped (%s)",type(exc).__name__)
        raise
