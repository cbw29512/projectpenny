"""Explicit opt-in for trusted internal memory-informed drafts."""
import logging
import re

logger = logging.getLogger(__name__)
INFORMED_PREFIX = "memory-informed:"


def submit_informed(store, key: str, task: str):
    """Internal adapter only. Public callers must always supply their own member ID."""
    try:
        if type(key) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", key):
            raise ValueError("invalid informed task key")
        if type(task) is not str or not task.strip() or len(task) > 2000 or "\x00" in task:
            raise ValueError("invalid informed task")
        return store.submit(None, INFORMED_PREFIX + key, task)
    except Exception as exc:
        logger.warning("Memory-informed submission rejected (%s)", type(exc).__name__)
        raise
