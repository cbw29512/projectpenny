"""Mocked network boundaries only; never contact Netlify."""
import base64
import hashlib
import hmac
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from penny.bridge.auth import bridge_token
from penny.bridge.transport import BridgeClient, MAX_RESPONSE_BYTES

KEY = b"k" * 32
HOST = "penny-preview.netlify.app"


class BridgeTransportTests(unittest.TestCase):
    def setUp(self):
        self.client = BridgeClient(HOST, KEY)
        self.id, self.owner, self.fence = uuid4(), uuid4(), uuid4()

    def claim_data(self):
        return {"status": "claimed", "id": str(self.id), "owner": str(self.owner),
                "fence": str(self.fence), "text": "Hello",
                "leaseUntil": (datetime.now(timezone.utc) + timedelta(minutes=5))
                .isoformat(timespec="milliseconds").replace("+00:00", "Z")}

    def response(self, connection, data=None, *, status=200, headers=None, raw=None):
        response = connection.return_value.getresponse.return_value
        response.status = status
        values = {"Content-Type": "application/json", **(headers or {})}
        response.getheader.side_effect = lambda k, default=None: values.get(k, default)
        response.read.return_value = json.dumps(data).encode() if raw is None else raw
        return response

    def test_host_and_key_validation(self):
        for host in ("localhost", "127.0.0.1", "https://site.netlify.app",
                     "site.netlify.app.evil", "site.netlify.app/path", "site.netlify.app:443"):
            with self.assertRaises(ValueError):
                BridgeClient(host, KEY)
        with self.assertRaises(ValueError):
            BridgeClient(HOST, b"weak")

    def test_token_matches_gateway_signature(self):
        token = bridge_token(KEY, now=1000)
        version, payload, sig = token.removeprefix("Bearer ").split(".")
        self.assertEqual(version, "v1")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        self.assertEqual(claims, {"aud": "bridge", "sub": "nucbox-bridge",
                                  "iat": 1000, "exp": 1300})
        expected = hmac.new(KEY, ("penny-beta-v1." + payload).encode(), hashlib.sha256).digest()
        self.assertEqual(sig, base64.urlsafe_b64encode(expected).decode().rstrip("="))

    @patch("penny.bridge.transport.PublicHTTPSConnection")
    def test_claim_uses_fixed_https_route_and_typed_response(self, connection):
        self.response(connection, self.claim_data())
        result = self.client.claim()
        self.assertEqual(result.status, "claimed")
        self.assertEqual(result.claim.id, self.id)
        self.assertEqual(result.claim.owner, self.owner)
        self.assertEqual(result.claim.fence, self.fence)
        args, kwargs = connection.call_args
        self.assertEqual(args, (HOST,))
        self.assertEqual(kwargs["port"], 443)
        self.assertTrue(kwargs["context"].check_hostname)
        args, kwargs = connection.return_value.request.call_args
        self.assertEqual(args, ("POST", "/api/v1/bridge/claim"))
        self.assertEqual(json.loads(kwargs["body"]), {})
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Bearer v1."))
        connection.return_value.close.assert_called_once()

    @patch("penny.bridge.transport.PublicHTTPSConnection")
    def test_untrusted_claim_fields_rejected(self, connection):
        for changes in ({"role": "administrator"}, {"text": "x" * 2001},
                        {"id": "invalid"}, {"leaseUntil": "2000-01-01T00:00:00.000Z"},
                        {"leaseUntil": "2099-01-01T00:00:00.000Z"}):
            self.response(connection, {**self.claim_data(), **changes})
            self.assertEqual(self.client.claim().status, "uncertain")

    @patch("penny.bridge.transport.PublicHTTPSConnection")
    def test_no_redirect_or_retry(self, connection):
        self.response(connection, status=302, headers={"Location": "http://localhost"})
        self.assertEqual(self.client.claim().status, "uncertain")
        connection.assert_called_once()

    @patch("penny.bridge.transport.PublicHTTPSConnection")
    def test_backoff_and_auth_failure(self, connection):
        self.response(connection, status=429, headers={"Retry-After": "3600"})
        self.assertEqual(self.client.claim().retry_after, 3600)
        self.response(connection, status=503, headers={"Retry-After": "0"})
        self.assertEqual(self.client.claim().retry_after, 60)
        self.response(connection, status=401)
        self.assertEqual(self.client.claim().status, "unauthorized")

    @patch("penny.bridge.transport.PublicHTTPSConnection")
    def test_reply_bound_and_duplicate_json(self, connection):
        response = self.response(connection, raw=b"x" * (MAX_RESPONSE_BYTES + 1))
        self.assertEqual(self.client.claim().status, "uncertain")
        response.read.assert_called_once_with(MAX_RESPONSE_BYTES + 1)
        self.response(connection, raw=b'{"status":"empty","status":"claimed"}')
        self.assertEqual(self.client.claim().status, "uncertain")

    @patch("penny.bridge.transport.PublicHTTPSConnection")
    def test_typed_upload_and_uncertain_network(self, connection):
        self.response(connection, {"status": "ok"})
        self.assertEqual(self.client.answer(self.id, self.fence, "Reply").status, "ok")
        self.assertEqual(connection.return_value.request.call_args.args[1], "/api/v1/bridge/answer")
        self.assertEqual(json.loads(connection.return_value.request.call_args.kwargs["body"]),
                         {"id": str(self.id), "fence": str(self.fence), "text": "Reply"})
        connection.return_value.request.side_effect = TimeoutError
        self.assertEqual(self.client.ack(self.id, self.fence, uuid4()).status, "uncertain")
        self.assertEqual(connection.call_count, 2)

    @patch("penny.bridge.transport.PublicHTTPSConnection")
    def test_invalid_upload_never_connects(self, connection):
        with self.assertRaises(ValueError):
            self.client.answer(self.id, self.fence, "x" * 16001)
        with self.assertRaises(ValueError):
            self.client.reject("untrusted", self.fence)
        connection.assert_not_called()
