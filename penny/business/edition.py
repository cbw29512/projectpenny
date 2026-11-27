"""Build a private branded edition under the existing shared review lock."""
import logging
from hashlib import sha256

from penny.guardian.policy import authorize
from penny.guardian.state import Actor,Capability
from penny.memory.review import _valid_id
from penny.scheduler.storage_db import locked
from .brand import matches_locked
from .quality import _latest,_verdict
from .workshop_intake import read_locked
from .edition_state import BrandedEdition
from .printable import printable

logger=logging.getLogger(__name__)


def build_private(dsn,task_id,*,review_id,source_sha256,brand_version,artwork):
    """Check exact current source and brand together; never write/publish."""
    try:
        if not _valid_id(task_id) or not _valid_id(review_id):
            raise ValueError("invalid edition identity")
        if not all(authorize(Actor.ADMIN,cap).allowed for cap in
                   (Capability.REVIEW_PRODUCT_CATALOG,Capability.REVIEW_BUSINESS_EXPERIMENT)):
            return None
        with locked(dsn) as (conn,_,now):
            row=_latest(conn,task_id)
            if (_verdict(row)!="passed" or row["id"]!=review_id
                    or row["content_sha256"]!=source_sha256):
                return None
            source=read_locked(conn,task_id,now)
            if not source or source["status"]!="private_prototype":
                return None
            data=source["artifact"]
            if (data["content_sha256"]!=source_sha256
                    or not matches_locked(conn,brand_version,artwork)):
                return None
            content=printable(data["content"],artwork)
            if content is None:
                return None
            return BrandedEdition(source_sha256,str(review_id),brand_version,
                                  sha256(artwork).hexdigest(),
                                  sha256(content).hexdigest(),content)
    except Exception as exc:
        logger.error("Private branded edition refused (%s)",type(exc).__name__)
        raise
