"""Exact signed Workshop observation; no private payload or arbitrary path."""
import hashlib
import hmac
import json
import logging
import ssl
import time
from penny.bridge.transport import _unique_pairs
from penny.bridge.public_https import PublicHTTPSConnection
from .workshop_source import STAGES

logger=logging.getLogger(__name__)
PATH="/api/v1/bridge/workshop"
DOMAIN="penny-workshop-publish-v1."


def signature(key,value,now):
    if (type(key) is not bytes or not 32<=len(key)<=64
            or type(value) is not dict or set(value)!={"sampled_at","stage","generated_at","expires_at"}
            or any(type(n) is not int or not 0<=n<2**53 for n in
                   (now,value["sampled_at"],value["generated_at"],value["expires_at"]))):
        raise ValueError("invalid Workshop observation")
    s,g,e,stage=(value[k] for k in ("sampled_at","generated_at","expires_at","stage"))
    if not 0<s<=now<s+15 or type(stage) is not str:
        raise ValueError("stale Workshop observation")
    if not ((stage=="unavailable" and g==e==0) or
            (stage in STAGES and 0<g<=s and now<e<=min(s+120,g+3600))):
        raise ValueError("invalid Workshop stage")
    return hmac.new(key,(DOMAIN+f"{s}.{stage}.{g}.{e}").encode("ascii"),hashlib.sha256).hexdigest()


def send(config,value):
    conn=None
    try:
        mac=signature(config.key,value,int(time.time()))
        body=json.dumps(value,separators=(",",":")).encode("ascii")
        conn=PublicHTTPSConnection(config.host,443,timeout=5,context=ssl.create_default_context())
        conn.request("POST",PATH,body=body,headers={
            "Authorization":"PennyWorkshop v1."+mac,"Content-Type":"application/json",
            "Accept":"application/json","Accept-Encoding":"identity","Cache-Control":"no-store"})
        response=conn.getresponse()
        if response.status in (429,503):
            return "backoff"
        if response.status in (401,403):
            return "unauthorized"
        if response.status==409:
            return "refused"
        if (response.status!=200 or response.getheader("Content-Encoding","identity").lower()!="identity"
                or response.getheader("Content-Type","").split(";")[0].strip().lower()!="application/json"):
            return "uncertain"
        raw=response.read(513)
        if len(raw)>512:
            return "uncertain"
        return "published" if json.loads(raw,object_pairs_hook=_unique_pairs)=={"status":"ok"} else "uncertain"
    except Exception as exc:
        logger.warning("Workshop transmission uncertain (%s)",type(exc).__name__)
        return "uncertain"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                logger.warning("Workshop connection cleanup failed")
