"""Explicit, bounded smoke test for Penny's own Netlify draft deployment."""
import argparse
import json
import logging
import re
import ssl
import time

from penny.bridge.public_https import PublicHTTPSConnection
from penny.bridge.transport import _unique_pairs

logger = logging.getLogger(__name__)
DRAFT = re.compile(r"[a-f0-9]{24}--projectpenny\.netlify\.app\Z")
ROUTES = (("read", "GET", "/api/v1/workshop", 6),
          ("write", "POST", "/api/v1/bridge/workshop", 3))


def request(host, method, path, operation):
    conn = None
    try:
        conn = PublicHTTPSConnection(host, 443, timeout=5,
                                     context=ssl.create_default_context())
        # No auth headers, product content, cookies, or credentials.
        conn.request(method, path, body=b"" if method == "POST" else None,
                     headers={"Accept": "application/json", "Accept-Encoding": "identity"})
        response = conn.getresponse()
        if response.status == 429:
            return "limited"
        if (response.status != 503
                or response.getheader("Content-Encoding", "identity").lower() != "identity"
                or response.getheader("Content-Type", "").split(";")[0].strip().lower()
                    != "application/json"):
            return "unexpected"
        body = response.read(513)
        if len(body) > 512:
            return "unexpected"
        value = json.loads(body, object_pairs_hook=_unique_pairs)
        return "smoke" if value == {"schema": "penny-workshop-smoke-v1",
                                     "status": "unavailable", "operation": operation} else "unexpected"
    except Exception as exc:
        logger.warning("Smoke request unavailable (%s)", type(exc).__name__)
        return "unexpected"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                logger.warning("Smoke connection cleanup failed")


def verify(host, *, confirmed=False, send=request, delay=time.sleep, clock=time.monotonic):
    """At most 13 requests total; never retry, follow redirects, or hit production."""
    try:
        if confirmed is not True or type(host) is not str or not DRAFT.fullmatch(host):
            return {"status": "refused", "requests": 0}
        count = 0
        results = {}
        for operation, method, path, limit in ROUTES:
            started = clock()
            saw_smoke = False
            for _ in range(limit + 1):
                result = send(host, method, path, operation)
                count += 1
                if result == "smoke":
                    saw_smoke = True
                elif result == "limited" and saw_smoke:
                    break
                else:
                    return {"status": "inconclusive", "requests": count}
            else:
                # Provider documents a possible ten-second enforcement lag.
                # Refuse a slow burst that could have crossed the limit window.
                if clock() - started > 35:
                    return {"status": "inconclusive", "requests": count}
                delay(11)
                result = send(host, method, path, operation)
                count += 1
                if result != "limited" or clock() - started >= 60:
                    return {"status": "inconclusive", "requests": count}
            results[operation] = "smoke_and_429_observed"
        return {"status": "observed", "requests": count, "routes": results}
    except Exception as exc:
        logger.error("Smoke verification failed (%s)", type(exc).__name__)
        return {"status": "inconclusive"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    result = verify(args.host, confirmed=args.confirm)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
