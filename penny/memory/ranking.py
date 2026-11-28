"""Bounded deterministic lexical query preparation and result selection."""
import logging
import re

from .maintenance_state import MAINTENANCE_PREFIX, MAINTENANCE_PROMPT, MAX_TOPIC_CHARS
from .review_state import (
    MAX_RECALL_CHARS, MAX_RECALL_RECORDS, MAX_SEARCH_TERMS, ReviewedMemory,
)

logger = logging.getLogger(__name__)


def search_expression(task: str) -> str:
    """Only plain terms reach PostgreSQL; operators are supplied by this adapter."""
    try:
        if type(task) is not str or not 1 <= len(task) <= 2000:
            raise ValueError("invalid search task")
        # Initial English lexical search; no user-supplied search syntax.
        terms = dict.fromkeys(word for word in re.findall(r"[a-z0-9]{2,32}", task.casefold())
                              if word != "or")
        return " OR ".join(list(terms)[:MAX_SEARCH_TERMS])
    except Exception as exc:
        logger.warning("Recall search input rejected (%s)", type(exc).__name__)
        raise


def task_search_expression(key: str, payload: str) -> str:
    """Use only the stored topic for a maintenance task, not its instructions."""
    try:
        if type(key) is not str or type(payload) is not str:
            raise ValueError("invalid stored recall task")
        if key.startswith(MAINTENANCE_PREFIX):
            if not payload.startswith(MAINTENANCE_PROMPT):
                return ""
            topic = payload[len(MAINTENANCE_PROMPT):]
            if not topic.strip() or len(topic) > MAX_TOPIC_CHARS or "\x00" in topic:
                return ""
            return search_expression(topic)
        return search_expression(payload)
    except Exception as exc:
        logger.warning("Stored recall query rejected (%s)", type(exc).__name__)
        raise


def select_ranked(rows) -> tuple[ReviewedMemory, ...]:
    """Keep complete, non-duplicate records in descending DB relevance order."""
    try:
        selected = []
        seen = set()
        remaining = MAX_RECALL_CHARS
        for row in rows:
            content = row["content"]
            normalized = " ".join(content.casefold().split())
            if normalized in seen or len(content) > remaining:
                continue
            selected.append(ReviewedMemory(row["source_task_id"], row["kind"], content))
            seen.add(normalized)
            remaining -= len(content)
            if len(selected) == MAX_RECALL_RECORDS:
                break
        return tuple(selected)
    except Exception as exc:
        logger.error("Ranked memory selection failed (%s)", type(exc).__name__)
        raise
