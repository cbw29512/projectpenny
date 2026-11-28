"""Local trusted operator gate; durable attempt accounting before network IO."""
import hashlib
import logging
import os
from uuid import uuid4
from penny.guardian.policy import identity_matches
from penny.scheduler.storage_db import locked
from penny.runtime.operator_control import _exclusive
from penny.bridge.public_https import HOST
from .workshop_snapshot import candidate_locked

logger=logging.getLogger(__name__)
LOCK_ID=724390581215034
RESULTS=frozenset(("published","refused","backoff","unauthorized","uncertain"))


def binding(config):
    if (type(config.host) is not str or not HOST.fullmatch(config.host)
            or type(config.key) is not bytes or not 32<=len(config.key)<=64):
        raise ValueError("invalid Workshop publication config")
    return hashlib.sha256(b"workshop-v1\0"+config.host.encode("ascii")+b"\0"+config.key).hexdigest()


def configure(config,*,enabled,limit=0,confirmed=False,reconciled=False):
    try:
        if (confirmed is not True or type(enabled) is not bool or type(limit) is not int
                or not (1<=limit<=1440 if enabled else limit==0)
                or type(reconciled) is not bool or (enabled and reconciled)):
            return False
        digest=binding(config) if enabled else None
        with _exclusive(config.dsn,LOCK_ID) as acquired:
            if not acquired:
                return False
            with locked(config.dsn) as (conn,control,now):
                row=conn.execute("SELECT * FROM workshop_delivery_control WHERE singleton").fetchone()
                if enabled and (control["paused"] or not identity_matches()
                        or row["last_result"] in ("interrupted","uncertain","unauthorized")):
                    return False
                if reconciled and (not control["paused"] or row["enabled"]):
                    return False
                # Disable/reconcile never resets counters or cooldown.
                conn.execute("""UPDATE workshop_delivery_control SET enabled=%s,
                    daily_limit=%s,config_sha256=%s,last_result=CASE WHEN %s
                    THEN 'refused' ELSE last_result END WHERE singleton""",
                    (enabled,limit,digest,reconciled))
                conn.execute("INSERT INTO workshop_delivery_review VALUES (%s,%s,%s,%s,%s,%s)",
                             (uuid4(),enabled,limit,digest,now,os.getuid()))
                return True
    except Exception as exc:
        logger.error("Workshop configuration refused (%s)",type(exc).__name__)
        return False


def reserve(config):
    """Caller holds exclusive session lock; reserve and sample in one transaction."""
    try:
        with locked(config.dsn) as (conn,control,now):
            row=conn.execute("SELECT * FROM workshop_delivery_control WHERE singleton").fetchone()
            if control["paused"] or not row["enabled"] or not identity_matches():
                return "paused",None
            if (row["config_sha256"]!=binding(config)
                    or row["last_result"] in ("interrupted","uncertain","unauthorized")):
                return "review_required",None
            if now<row["not_before"] or now//86400<row["day_bucket"]:
                return "cooldown",None
            bucket=now//86400
            attempts=row["attempts"] if bucket==row["day_bucket"] else 0
            if attempts>=row["daily_limit"]:
                return "budget_exhausted",None
            candidate=candidate_locked(conn,now)
            if candidate["status"]=="reviewed":
                value={"sampled_at":now,"stage":candidate["stage"],
                       "generated_at":candidate["generated_at"],
                       "expires_at":min(candidate["expires_at"],now+120)}
            else:
                value={"sampled_at":now,"stage":"unavailable","generated_at":0,"expires_at":0}
            conn.execute("""UPDATE workshop_delivery_control SET day_bucket=%s,attempts=%s,
                not_before=%s,last_result='interrupted' WHERE singleton""",(bucket,attempts+1,now+60))
            return "reserved",value
    except Exception as exc:
        logger.error("Workshop reservation refused (%s)",type(exc).__name__)
        raise


def finish(dsn,result):
    try:
        if result not in RESULTS:
            result="uncertain"
        with locked(dsn) as (conn,_,now):
            row=conn.execute("""UPDATE workshop_delivery_control SET last_result=%s,
                enabled=enabled AND NOT %s,not_before=GREATEST(not_before,%s)
                WHERE singleton AND last_result='interrupted' RETURNING singleton""",
                (result,result in ("uncertain","unauthorized"),now+300 if result=="backoff" else now)).fetchone()
            if not row:
                raise RuntimeError("Workshop completion not recorded")
    except Exception as exc:
        logger.error("Workshop completion refused (%s)",type(exc).__name__)
        raise
