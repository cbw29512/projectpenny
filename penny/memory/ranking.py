"""Bounded deterministic lexical query preparation and result selection."""
import logging
import re

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
        terms = dict.fromkeys(re.findall(r"[a-z0-9]{2,32}", task.casefold()))
        return " OR ".join(list(terms)[:MAX_SEARCH_TERMS])
    except Exception as exc:
        logger.warning("Recall search input rejected (%s)", type(exc).__name__)
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
