"""Synthetic artwork approval, byte integrity and permanent revocation."""
import unittest
from hashlib import sha256
from unittest.mock import patch
from uuid import uuid4

from database_fixture import DSN, DatabaseFixture
from penny.business.brand import approve, revoke, matches_locked
from penny.scheduler.storage_db import locked


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class BrandTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer = uuid4()
        self.artwork = b"synthetic artwork fixture only"
        self.args = dict(artwork=self.artwork,
                         expected_sha256=sha256(self.artwork).hexdigest(),
                         reviewer_id=self.reviewer, rights_ref="test:rights",
                         evidence=b"synthetic approval", confirmed=True)

    def approve(self, version="v1", **changes):
        return approve(self.dsn, version, **(self.args | changes))

    def matches(self, version="v1", artwork=None):
        with locked(self.dsn) as (conn, _, now):
            return matches_locked(conn, version,
                                  self.artwork if artwork is None else artwork)

    def revoke(self, version="v1"):
        return revoke(self.dsn, version, reviewer_id=self.reviewer,
                      evidence_ref="test:withdraw", evidence=b"synthetic withdrawal",
                      confirmed=True)

    def test_unapproved_changed_and_invalid_bytes_rejected(self):
        self.assertFalse(self.matches())
        self.assertFalse(self.approve(expected_sha256="a" * 64))
        with self.assertRaises(ValueError):
            self.approve(confirmed=False)
        self.assertTrue(self.approve())
        self.assertTrue(self.matches())
        self.assertFalse(self.matches(artwork=b"changed"))
        self.assertFalse(self.matches(artwork=b""))
        self.assertFalse(self.matches(artwork="not bytes"))
        self.assertFalse(self.matches("missing"))
        self.assertFalse(self.approve())
        with self.assertRaises(ValueError):
            self.approve(rights_ref="test:changed")

    def test_single_active_version_and_no_reactivation(self):
        self.assertTrue(self.approve())
        self.assertFalse(self.approve("v2"))
        self.assertTrue(self.revoke())
        self.assertFalse(self.revoke())
        self.assertFalse(self.matches())
        self.assertFalse(self.approve())
        self.assertTrue(self.approve("v2"))
        self.assertTrue(self.matches("v2"))
        self.assertFalse(self.matches("v1"))

    def test_guardian_refusal(self):
        with patch("penny.business.brand.authorize") as authorization:
            authorization.return_value.allowed = False
            self.assertFalse(self.approve())
            self.assertFalse(self.revoke())
        self.assertFalse(self.matches())
