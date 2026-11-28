"""Immutable private derived edition; not a release approval."""
from dataclasses import dataclass, field

FORMAT = "penny-checklist-print-html-v1"


@dataclass(frozen=True, slots=True)
class BrandedEdition:
    source_sha256: str
    quality_review_id: str
    brand_version: str
    artwork_sha256: str
    edition_sha256: str
    content: bytes = field(repr=False)
    format_version: str = FORMAT

    def manifest(self):
        return {"format_version": self.format_version,
                "source_sha256": self.source_sha256,
                "quality_review_id": self.quality_review_id,
                "brand_version": self.brand_version,
                "artwork_sha256": self.artwork_sha256,
                "edition_sha256": self.edition_sha256,
                "commercial_release_authorized": False}
