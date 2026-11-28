"""Strict parser for an untrusted model-generated maintenance proposal."""
import json
import logging
from uuid import UUID

from .intake import _unique_object
from .maintenance_state import MaintenanceAction, MaintenanceProposal

logger = logging.getLogger(__name__)


def _text(value, maximum):
    if type(value) is not str or not 1 <= len(value.strip()) <= maximum or "\x00" in value:
        raise ValueError("invalid proposal text")
    value.encode("utf-8")
    if len(value) > maximum:
        raise ValueError("proposal text too large")
    return value.strip()


def parse_maintenance(raw: object) -> MaintenanceProposal | None:
    try:
        if type(raw) is not str or len(raw) > 8000:
            return None
        data = json.loads(raw, object_pairs_hook=_unique_object)
        if type(data) is not dict or set(data) != {"action","sources","rationale","replacement"}:
            return None
        if type(data["action"]) is not str:
            return None
        action = MaintenanceAction(data["action"])
        sources = data["sources"]
        if type(sources) is not list or not 1 <= len(sources) <= 3:
            return None
        ids = []
        for source in sources:
            if type(source) is not str:
                return None
            parsed = UUID(source)
            if str(parsed) != source or parsed.int == 0 or parsed in ids:
                return None
            ids.append(parsed)
        if action in (MaintenanceAction.CORRECT, MaintenanceAction.OUTDATED) and len(ids) != 1:
            return None
        if action in (MaintenanceAction.CONSOLIDATE, MaintenanceAction.CONTRADICTION) and len(ids) < 2:
            return None
        replacement = data["replacement"]
        if action in (MaintenanceAction.CORRECT, MaintenanceAction.CONSOLIDATE):
            replacement = _text(replacement,1000)
        elif replacement is not None:
            return None
        return MaintenanceProposal(action,tuple(ids),_text(data["rationale"],500),replacement)
    except (ValueError, TypeError, RecursionError):
        logger.info("Memory maintenance proposal rejected")
        return None
