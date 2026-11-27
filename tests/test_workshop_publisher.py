"""Persistent Workshop delivery budget and signature; no real network."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import hashlib
import hmac
from database_fixture import DSN,DatabaseFixture
from penny.progress.workshop_gate import configure,reserve,finish
from penny.progress.workshop_publisher import publish_once
from penny.progress.workshop_wire import signature
from penny.runtime.operator_control import stop


class SignatureTests(unittest.TestCase):
    def test_exact_domain_and_expiry(self):
        key=b"x"*32
        v=dict(sampled_at=1000,stage="prototype_reviewed",generated_at=990,expires_at=1100)
        self.assertEqual(signature(key,v,1000),hmac.new(key,
            b"penny-workshop-publish-v1.1000.prototype_reviewed.990.1100",hashlib.sha256).hexdigest())
        for bad in (v|{"private":"secret"},v|{"expires_at":1121},v|{"stage":"released"}):
            with self.assertRaises(ValueError):
                signature(key,bad,1000)
        with self.assertRaises(ValueError):
            signature(key,v,1015)


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class WorkshopGateTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.config=SimpleNamespace(dsn=self.dsn,host="penny.example",key=b"x"*32)

    def test_default_closed_and_stop(self):
        self.assertEqual(publish_once(self.config,confirmed=True),"paused")
        self.assertTrue(configure(self.config,enabled=True,limit=1,confirmed=True))
        with patch("penny.progress.workshop_publisher.send",return_value="published") as send:
            self.assertEqual(publish_once(self.config,confirmed=True),"published")
            self.assertEqual(send.call_args.args[1]["stage"],"unavailable")
            self.assertEqual(publish_once(self.config,confirmed=True),"cooldown")
            self.assertTrue(stop(self.dsn))
            self.assertEqual(publish_once(self.config,confirmed=True),"paused")
            send.assert_called_once()

    def test_interrupted_requires_reconciliation(self):
        self.assertTrue(configure(self.config,enabled=True,limit=1,confirmed=True))
        self.assertEqual(reserve(self.config)[0],"reserved")
        self.assertEqual(reserve(self.config)[0],"review_required")
        self.assertFalse(configure(self.config,enabled=True,limit=1,confirmed=True))
        self.assertTrue(stop(self.dsn))
        self.assertTrue(configure(self.config,enabled=False,confirmed=True,reconciled=True))
        self.assertEqual(reserve(self.config)[0],"paused")
