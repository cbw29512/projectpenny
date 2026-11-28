"""Human attestations for a fixed checklist review rubric."""
from dataclasses import dataclass,field

CRITERIA=("usefulness","accuracy","originality","privacy","completeness")


@dataclass(frozen=True,slots=True)
class PrivateExport:
    filename: str
    media_type: str
    content_sha256: str
    content: bytes=field(repr=False)
