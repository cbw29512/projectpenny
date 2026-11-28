"""Evidence fingerprints establish integrity, never truth or authorization."""
from dataclasses import dataclass
from hashlib import sha256
import logging
from uuid import UUID

logger = logging.getLogger(__name__)
MAX_EVIDENCE_BYTES = 16384


@dataclass(frozen=True, slots=True)
class EvidenceFingerprint:
    source_task_id: UUID
    digest: str
    byte_count: int


def fingerprint(source_task_id: UUID, material: bytes) -> EvidenceFingerprint:
    """Bind bounded evidence bytes to an externally supplied source identifier."""
    try:
        if type(source_task_id) is not UUID or source_task_id.int == 0:
            raise ValueError("invalid evidence source identifier")
        if type(material) is not bytes or not 1 <= len(material) <= MAX_EVIDENCE_BYTES:
            raise ValueError("invalid evidence size or type")
        return EvidenceFingerprint(source_task_id, sha256(material).hexdigest(), len(material))
    except (ValueError, TypeError):
        # Never expose evidence bytes or student/member information in logs.
        logger.warning("Evidence fingerprint rejected")
        raise
