"""Restricted HTTPS client, no redirect, proxy, arbitrary URL or retries."""
import json
import logging
import re
import ssl
from datetime import datetime, timezone
from uuid import UUID

from .auth import bridge_token
from .state import BridgeResult, parse_claim, wire_text

logger = logging.getLogger(__name__)
from .public_https import HOST, PublicHTTPSConnection
MAX_RESPONSE_BYTES = 16384
PATHS = {op: "/api/v1/bridge/" + op for op in ("claim", "ack", "answer", "reject")}


def _identifier(value):
    if type(value) is not UUID or value.int == 0:
        raise ValueError("invalid identifier")
    return str(value)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class BridgeClient:
    def __init__(self, host, key, *, timeout=10):
        # Explicit operator-selected Netlify hostname only; no remote URLs.
        if (type(host) is not str or not HOST.fullmatch(host)
                or type(key) is not bytes or len(key) < 32
                or type(timeout) not in (int, float) or not 1 <= timeout <= 15):
            raise ValueError("invalid bridge configuration")
        self._host, self._key, self._timeout = host, key, timeout

    def claim(self):
        return self._send("claim", {})

    def ack(self, question_id, fence, local_task):
        return self._send("ack", {"id": _identifier(question_id),
                                  "fence": _identifier(fence),
                                  "localTask": _identifier(local_task)})

    def answer(self, question_id, fence, text):
        return self._send("answer", {"id": _identifier(question_id),
                                     "fence": _identifier(fence),
                                     "text": wire_text(text, 16000)})

    def reject(self, question_id, fence):
        return self._send("reject", {"id": _identifier(question_id),
                                     "fence": _identifier(fence)})

    def _send(self, op, body):
        conn = None
        try:
            if op not in PATHS:
                raise ValueError("unsupported bridge operation")
            # Compact UTF-8 keeps even 16k Unicode replies within gateway cap.
            wire = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if len(wire) > 100000:
                raise ValueError("oversized wire request")
            conn = PublicHTTPSConnection(self._host, port=443,
                timeout=self._timeout, context=ssl.create_default_context())
            conn.request("POST", PATHS[op], body=wire, headers={
                "Authorization": bridge_token(self._key),
                "Content-Type": "application/json", "Accept": "application/json",
                "Accept-Encoding": "identity", "Cache-Control": "no-store",
            })
            response = conn.getresponse()
            if response.status in (429, 503):
                # Refuse tight retry loops, even if the remote header is bad.
                raw = response.getheader("Retry-After", "")
                delay = int(raw) if re.fullmatch(r"[0-9]{1,6}", raw) else 60
                return BridgeResult("backoff", retry_after=max(60, min(delay, 86400)))
            if response.status in (401, 403):
                return BridgeResult("unauthorized")
            if response.status == 409:
                return BridgeResult("conflict")
            if response.status != 200:
                raise ValueError("unexpected HTTP status")
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise ValueError("compressed response rejected")
            if response.getheader("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                raise ValueError("unexpected response type")
            length = response.getheader("Content-Length")
            if length is not None and (not re.fullmatch(r"[0-9]{1,8}", length)
                    or int(length) > MAX_RESPONSE_BYTES):
                raise ValueError("oversized response")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES or (length is not None and len(raw) != int(length)):
                raise ValueError("invalid response length")
            data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
            if op == "claim":
                if data == {"status": "empty"}:
                    return BridgeResult("empty")
                return BridgeResult("claimed", parse_claim(data, datetime.now(timezone.utc)))
            if data != {"status": "ok"}:
                raise ValueError("invalid acknowledgement")
            return BridgeResult("ok")
        except Exception as exc:
            # An upload/claim may have committed remotely. Never retry here.
            logger.warning("Bridge operation uncertain (%s)", type(exc).__name__)
            return BridgeResult("uncertain")
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    logger.warning("Bridge connection cleanup failed")
