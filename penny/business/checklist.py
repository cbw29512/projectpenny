"""Render a validated JSON checklist as inert, printable UTF-8 text."""
import json
import logging
from .draft_parse import _unique
from .store import _text

logger=logging.getLogger(__name__)


def render_checklist(raw):
    try:
        if type(raw) is not str or not 1<=len(raw)<=8000:
            return None
        data=json.loads(raw,object_pairs_hook=_unique)
        if type(data) is not dict or set(data)!={"title","instructions","items"}:
            return None
        if not _text(data["title"],120) or not _text(data["instructions"],400):
            return None
        items=data["items"]
        if (type(items) is not list or not 3<=len(items)<=12
                or not all(_text(item,300) for item in items)
                or len({item.strip().casefold() for item in items})!=len(items)):
            return None
        # No HTML, file path, executable code, or external URL is interpreted.
        # Display as plain text only; human review remains required.
        lines=[data["title"].strip(),"",data["instructions"].strip(),"",
               *("[ ] "+item.strip() for item in items),""]
        content="\n".join(lines)
        return content if len(content)<=6000 else None
    except (ValueError,TypeError,RecursionError):
        logger.info("Checklist output rejected: invalid shape")
        return None
