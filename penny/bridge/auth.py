"""Short-lived bridge-only bearer credentials matching the beta gateway."""
import base64
import hashlib
import hmac
import json
import logging
import time

logger = logging.getLogger(__name__)


def _b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def bridge_token(key, *, now=None):
    try:
        if type(key) is not bytes or len(key) < 32:
            raise ValueError("strong bridge key required")
        t = int(time.time()) if now is None else now
        if type(t) is not int or not 0 < t < 2**53 - 300:
            raise ValueError("invalid credential clock")
        # Bridge key can never sign member credentials.
        payload = _b64(json.dumps({
            "aud": "bridge", "sub": "nucbox-bridge",
            "iat": t, "exp": t + 300,
        }, separators=(",", ":")).encode("utf-8"))
        sig = hmac.new(key, ("penny-beta-v1." + payload).encode("ascii"),
                       hashlib.sha256).digest()
        return "Bearer v1." + payload + "." + _b64(sig)
    except Exception:
        logger.error("Bridge credential creation failed")
        raise
