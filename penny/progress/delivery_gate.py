"""Persistent outbound observation attempt budget; separate from task admission."""
import hashlib
import logging
import os
from uuid import uuid4

from penny.guardian.policy import identity_matches
from penny.scheduler.storage_db import locked
from penny.runtime.operator_control import _exclusive
from penny.bridge.transport import HOST
from .activity_db import activity_call

logger=logging.getLogger(__name__)
LOCK_ID=724390581215033
INTERVAL=60
RESULTS=frozenset(("published","refused","unavailable","backoff","unauthorized","uncertain"))


def binding(config):
    # Bind approval to endpoint and secret, never print the fingerprint.
    if (type(config.host) is not str or not HOST.fullmatch(config.host)
            or type(config.key) is not bytes or not 32<=len(config.key)<=64):
        raise ValueError("invalid projection configuration")
    return hashlib.sha256(config.host.encode("ascii")+b"\0"+config.key).hexdigest()


def configure(config,*,enabled,limit=0,confirmed=False):
    try:
        if (confirmed is not True or type(enabled) is not bool or type(limit) is not int
                or not (1<=limit<=1440 if enabled else limit==0)):
            return False
        digest=binding(config) if enabled else None
        with _exclusive(config.dsn,LOCK_ID) as acquired:
            if not acquired:
                return False
            with locked(config.dsn) as (conn,control,now):
                if enabled and (control["paused"] or not identity_matches()):
                    return False
                # Never reset a daily bucket or bypass the prior cooldown.
                conn.execute("""UPDATE activity_delivery_control
                    SET enabled=%s,daily_limit=%s,config_sha256=%s WHERE singleton""",
                    (enabled,limit,digest))
                conn.execute("""INSERT INTO activity_delivery_review
                    VALUES (%s,%s,%s,%s,%s,%s)""",
                    (uuid4(),enabled,limit,digest,now,os.getuid()))
                return True
    except Exception as exc:
        logger.error("Activity configuration refused (%s)",type(exc).__name__)
        return False


def reserve(config):
    # Python identity check remains mandatory; database owns the durable cap.
    if not identity_matches():
        return "paused"
    result=activity_call(config.dsn,"reserve",(binding(config),))["result"]
    if result not in ("reserved","paused","review_required","cooldown","budget_exhausted"):
        raise RuntimeError("unexpected activity reservation")
    return result


def finish(dsn,result):
    if result not in RESULTS:
        result="uncertain"
    if activity_call(dsn,"finish",(result,))["result"] is not True:
        raise RuntimeError("activity completion not recorded")


def clear_interrupted(dsn,*,confirmed=False):
    """After operator reconciliation; does not enable publication."""
    try:
        if confirmed is not True:
            return False
        with _exclusive(dsn,LOCK_ID) as acquired:
            if not acquired:
                return False
            with locked(dsn) as (conn,_,now):
                row=conn.execute("""UPDATE activity_delivery_control
                    SET enabled=false,last_result='uncertain'
                    WHERE singleton AND last_result='interrupted' RETURNING daily_limit""").fetchone()
                if not row:
                    return False
                conn.execute("INSERT INTO activity_delivery_review VALUES (%s,false,0,NULL,%s,%s)",
                             (uuid4(),now,os.getuid()))
                return True
    except Exception as exc:
        logger.error("Activity recovery refused (%s)",type(exc).__name__)
        return False
