"""Shared scheduler rest restriction. Always evaluated under scheduler lock."""
import logging
from penny.progress.rest_schedule import window_at

logger = logging.getLogger(__name__)


def rest_closed(control, now):
    """Invalid enabled policy/clock closes the gate; disabled is explicit."""
    try:
        enabled = control["rest_enabled"]
        if type(enabled) is not bool:
            return True
        if not enabled:
            return False
        window = window_at(now)
        return window is None or window.scheduled_rest
    except Exception as exc:
        logger.error("Rest gate failed closed (%s)", type(exc).__name__)
        return True
