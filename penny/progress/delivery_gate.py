"""Persistent outbound observation attempt budget; separate from task admission."""
import hashlib
import logging
import os
from uuid import uuid4

from penny.guardian.policy import identity_matches
from penny.scheduler.storage_db import locked
from penny.runtime.operator_control import _exclusive
from penny.bridge.transport import HOST

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
    with locked(config.dsn) as (conn,control,now):
        row=conn.execute("SELECT * FROM activity_delivery_control WHERE singleton FOR UPDATE").fetchone()
        if (not row or not row["enabled"] or control["paused"] or not identity_matches()
                or row["config_sha256"]!=binding(config)):
            return "paused"
        if row["last_result"]=="interrupted":
            return "review_required"
        if now<row["not_before"]:
            return "cooldown"
        day=max(now//86400,row["day_bucket"])
        count=row["attempts"] if day==row["day_bucket"] else 0
        if count>=row["daily_limit"]:
            return "budget_exhausted"
        # Consume an attempt before external effects, even if process dies.
        conn.execute("""UPDATE activity_delivery_control SET day_bucket=%s,
            attempts=%s,not_before=%s,last_result='interrupted' WHERE singleton""",
            (day,count+1,now+INTERVAL))
        return "reserved"


def finish(dsn,result):
    if result not in RESULTS:
        result="uncertain"
    with locked(dsn) as (conn,_,now):
        # A provider throttle has no approved retry budget. Stop on any failure.
        # Preserve emergency stop and never re-enable here.
        conn.execute("""UPDATE activity_delivery_control SET last_result=%s,
            enabled=enabled AND %s,not_before=greatest(not_before,%s)
            WHERE singleton AND last_result='interrupted'""",
            (result,result=="published",now+(86400 if result=="backoff" else INTERVAL)))


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
