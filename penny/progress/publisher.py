"""Explicit one-shot activity publisher; never send task content or inference."""
import hashlib
import hmac
import http.client
import json
import logging
import ssl
import time

from penny.bridge.transport import HOST, _unique_pairs
from penny.progress.activity import browser_candidate

logger = logging.getLogger(__name__)
PATH = "/api/v1/bridge/activity"
STATES = frozenset(("idle","working","draining","paused","blocked","off_duty"))
DOMAIN = "penny-activity-publish-v1."


def signature(key, sample, activity):
    """Domain-separated MAC binds the exact timestamp and enum, not arbitrary data."""
    if (type(key) is not bytes or not 32 <= len(key) <= 64
            or type(sample) is not int or not 0 < sample < 2**53
            or type(activity) is not str or activity not in STATES):
        raise ValueError("invalid activity signature input")
    return hmac.new(key,(DOMAIN+str(sample)+"."+activity).encode("ascii"),
                    hashlib.sha256).hexdigest()


def publish_once(config, *, confirmed=False):
    """Explicit operator action; no automatic retry or runtime state change."""
    conn = None
    try:
        if confirmed is not True or type(config.host) is not str or not HOST.fullmatch(config.host):
            return "refused"
        if type(config.key) is not bytes or not 32 <= len(config.key) <= 64:
            return "refused"
        candidate = browser_candidate(config.dsn)
        now = int(time.time())
        if (type(candidate) is not dict or set(candidate) !=
                {"schema","status","state","sampled_at","expires_at"}
                or candidate["schema"] != "penny-activity-v1"
                or candidate["status"] != "reviewed"
                or type(candidate["sampled_at"]) is not int
                or type(candidate["expires_at"]) is not int
                or candidate["expires_at"]-candidate["sampled_at"] != 15
                or not candidate["sampled_at"] <= now < candidate["expires_at"]):
            return "unavailable"
        sample, activity = candidate["sampled_at"], candidate["state"]
        mac = signature(config.key, sample, activity)
        wire = json.dumps({"sampled_at":sample,"activity":activity},
                          separators=(",",":")).encode("ascii")
        # Local candidate DB transaction has already ended before HTTPS.
        conn = http.client.HTTPSConnection(config.host,443,timeout=5,
                                          context=ssl.create_default_context())
        conn.request("POST",PATH,body=wire,headers={
            "Authorization":"PennyActivity v1."+mac,
            "Content-Type":"application/json","Accept":"application/json",
            "Accept-Encoding":"identity","Cache-Control":"no-store"})
        response = conn.getresponse()
        if response.status in (429,503):
            return "backoff"
        if response.status in (401,403):
            return "unauthorized"
        if response.status == 409:
            return "refused"
        if (response.status != 200
                or response.getheader("Content-Encoding","identity").lower()!="identity"
                or response.getheader("Content-Type","").split(";")[0].strip().lower()!="application/json"):
            return "uncertain"
        raw = response.read(513)
        if len(raw)>512:
            return "uncertain"
        return "published" if json.loads(raw,object_pairs_hook=_unique_pairs)=={"status":"ok"} else "uncertain"
    except Exception as exc:
        logger.warning("Activity publication uncertain (%s)",type(exc).__name__)
        return "uncertain"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                logger.warning("Activity connection cleanup failed")
