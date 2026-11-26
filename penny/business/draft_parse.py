"""Strict output schema; a valid shape is not evidence of market demand."""
import json
import logging
from .draft_state import Draft
from .state import Category,Metric,MAX_REVIEW
from .store import _text

logger=logging.getLogger(__name__)


def _unique(pairs):
    out={}
    for key,value in pairs:
        if key in out:
            raise ValueError("duplicate field")
        out[key]=value
    return out


def parse_draft(raw):
    try:
        if type(raw) is not str or not 1<=len(raw)<=8000:
            return None
        value=json.loads(raw,object_pairs_hook=_unique)
        if type(value) is not dict or set(value)!={
            "category","title","hypothesis","metric","target","duration_seconds",
            "additional_cash_cents"}:
            return None
        if (not _text(value["title"],120) or not _text(value["hypothesis"],1000)
                or type(value["category"]) is not str or type(value["metric"]) is not str
                or type(value["target"]) is not int or not 1<=value["target"]<=10000
                or type(value["duration_seconds"]) is not int
                or not 60<=value["duration_seconds"]<=MAX_REVIEW
                or type(value["additional_cash_cents"]) is not int
                or value["additional_cash_cents"]!=0):
            return None
        return Draft(Category(value["category"]),value["title"],value["hypothesis"],
                     Metric(value["metric"]),value["target"],value["duration_seconds"])
    except (ValueError,TypeError,RecursionError):
        logger.info("Business draft rejected: invalid shape")
        return None
