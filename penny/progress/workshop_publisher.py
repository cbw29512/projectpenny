"""Explicit trusted local publication, no timer or worker credentials yet."""
import logging
from penny.runtime.operator_control import _exclusive
from .workshop_gate import LOCK_ID,reserve,finish
from .workshop_wire import send

logger=logging.getLogger(__name__)


def publish_once(config,*,confirmed=False):
    try:
        if confirmed is not True:
            return "refused"
        with _exclusive(config.dsn,LOCK_ID) as acquired:
            if not acquired:
                return "busy"
            result,value=reserve(config)
            if result!="reserved":
                return result
            result=send(config,value)
            finish(config.dsn,result)
            return result
    except Exception as exc:
        logger.error("Workshop publication blocked (%s)",type(exc).__name__)
        return "uncertain"
