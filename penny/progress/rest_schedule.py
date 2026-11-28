"""Pure candidate rest schedule; no permission to stop or start a worker."""
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
ZONE = ZoneInfo("America/New_York")
POLICY_VERSION = "rest-concept-v1"


@dataclass(frozen=True, slots=True)
class RestWindow:
    local_date: str
    scheduled_rest: bool
    next_transition: int


def window_at(epoch_seconds: int) -> RestWindow | None:
    """Midnight to 08:00 Eastern wall time; DST handled by zoneinfo."""
    try:
        if type(epoch_seconds) is not int:
            return None
        local = datetime.fromtimestamp(epoch_seconds, timezone.utc).astimezone(ZONE)
        if not 2000 <= local.year <= 2099:
            return None
        resting = local.hour < 8
        target = local.date() if resting else local.date() + timedelta(days=1)
        transition = datetime.combine(target, time(8 if resting else 0), ZONE)
        return RestWindow(local.date().isoformat(), resting, int(transition.timestamp()))
    except Exception as exc:
        logger.error("Rest window unavailable (%s)", type(exc).__name__)
        return None
