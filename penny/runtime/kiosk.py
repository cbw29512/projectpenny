"""Loopback-only read-only kiosk, separate from inference and operator authority."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
from pathlib import Path

import psycopg

from .config import load_config

logger = logging.getLogger(__name__)
PORT = 18787
ROOT = Path(__file__).resolve().parents[2]
ASSETS = {
    "/": (ROOT / "kiosk/index.html", "text/html; charset=utf-8"),
    "/kiosk.css": (ROOT / "kiosk/kiosk.css", "text/css; charset=utf-8"),
    "/kiosk.mjs": (ROOT / "kiosk/kiosk.mjs", "text/javascript; charset=utf-8"),
    "/state.mjs": (ROOT / "kiosk/state.mjs", "text/javascript; charset=utf-8"),
    "/emotion.mjs": (ROOT / "kiosk/emotion.mjs", "text/javascript; charset=utf-8"),
    "/penny.svg": (ROOT / "website/assets/penny-preview.svg", "image/svg+xml"),
}


def snapshot(dsn):
    # One statement, one consistent database snapshot. No lock on the scheduler.
    with psycopg.connect(dsn, connect_timeout=3) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout='3s'")
        row = conn.execute("SELECT snapshot FROM kiosk_snapshot").fetchone()
        if row is None:
            raise RuntimeError("kiosk projection missing")
        return row[0]


class KioskServer(HTTPServer):
    def get_request(self):
        sock, addr = super().get_request()
        sock.settimeout(5)
        return sock, addr


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        # Request URLs and headers are not logged.
        pass

    def send_body(self, code, media_type, body):
        self.send_response(code)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; style-src 'self'; "
                         "img-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
                         "base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Reject DNS rebinding and cross-origin browser reads. No public route.
        if self.headers.get("Host") != f"127.0.0.1:{PORT}":
            self.send_body(403, "text/plain", b"Forbidden")
            return
        if self.headers.get("Sec-Fetch-Site") not in (None, "none", "same-origin"):
            self.send_body(403, "text/plain", b"Forbidden")
            return
        try:
            if self.path == "/api/state":
                body = json.dumps(snapshot(self.server.dsn)).encode("utf-8")
                self.send_body(200, "application/json", body)
            elif self.path in ASSETS:
                path, media_type = ASSETS[self.path]
                self.send_body(200, media_type, path.read_bytes())
            else:
                self.send_body(404, "text/plain", b"Not found")
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            logger.warning("Kiosk read unavailable (%s)", type(exc).__name__)
            try:
                self.send_body(503, "application/json", b'{"status":"unavailable"}')
            except OSError:
                pass


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    try:
        # Same strict private-file format; provision a kiosk-only DB role.
        dsn = load_config(args.config, "operator").dsn
        snapshot(dsn)
        with KioskServer(("127.0.0.1", PORT), Handler) as server:
            server.dsn = dsn
            logger.info("Private kiosk ready on loopback port %d", PORT)
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        logger.error("Kiosk stopped (%s)", type(exc).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
