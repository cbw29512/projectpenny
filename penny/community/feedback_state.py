"""Fixed, version-bound feedback values; no instructions or free text."""
from dataclasses import dataclass
import re
from uuid import UUID


@dataclass(frozen=True,slots=True)
class FeedbackReceipt:
    status: str
    feedback_id: UUID|None=None
    replay: bool=False


def validate_feedback(preview_id,preview_sha256,key,usefulness,purchase_interest):
    if (type(preview_id) is not UUID or preview_id.int==0
            or type(preview_sha256) is not str or not re.fullmatch(r"[a-f0-9]{64}",preview_sha256)
            or type(key) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}",key)
            or type(usefulness) is not int or not 1<=usefulness<=5
            or type(purchase_interest) is not str or purchase_interest not in ("yes","maybe","no")):
        raise ValueError("invalid feedback")
