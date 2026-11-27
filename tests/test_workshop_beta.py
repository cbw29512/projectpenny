"""Synthetic closed-beta delivery through existing authenticated sessions."""
import time
from contextlib import contextmanager
import unittest
from hashlib import sha256
from uuid import uuid4
from unittest.mock import patch

import test_showroom_feedback as fixture
from database_fixture import DSN
from penny.auth.session import issue_session,revoke_session
from penny.business.brand import approve,revoke
from penny.business.quality import review
from penny.business.quality_state import CRITERIA
from penny.business.beta_proof import prepare_beta
from penny.business.beta_grants import grant_beta,revoke_beta
from penny.business.beta_access import read_beta
from penny.business.preview import withdraw
from test_printable import png_fixture


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class BetaGrantTests(fixture.FeedbackFixture):
    def setUp(self):
        super().setUp()
        self.owner=uuid4()
        self.tester=issue_session(self.dsn,self.owner).token
        self.art=png_fixture()
        self.version="synthetic-beta"
        self.grant=uuid4()
        self.quality=review(self.dsn,self.task,source_ref="test:beta-quality",
            expected_content_sha256=self.digest,checks={k:True for k in CRITERIA},
            revoked=False,reviewer_id=self.reviewer,evidence_ref="test:quality",
            evidence=b"synthetic quality",confirmed=True).entry_id
        self.assertTrue(approve(self.dsn,self.version,artwork=self.art,
            expected_sha256=sha256(self.art).hexdigest(),reviewer_id=self.reviewer,
            rights_ref="test:brand",evidence=b"synthetic",confirmed=True))
        self.proof=prepare_beta(self.dsn,self.preview,self.grant,
            quality_review_id=self.quality,brand_version=self.version,artwork=self.art)
        self.args=dict(preview_id=self.preview,member_id=self.owner,
            quality_review_id=self.quality,brand_version=self.version,
            edition_sha256=self.proof.edition_sha256,variant_sha256=self.proof.variant_sha256,
            artwork=self.art,reviewer_id=self.reviewer,evidence_ref="test:beta",
            evidence=b"synthetic beta authorization",expires_at=int(time.time())+120,
            confirmed=True)

    def approve_grant(self,**changes):
        return grant_beta(self.dsn,self.grant,**(self.args|changes))

    def read(self,token=None,**changes):
        return read_beta(self.dsn,token or self.tester,self.grant,**({"artwork":self.art}|changes))

    def test_exact_variant_and_owner_only(self):
        self.assertIsNone(self.read())
        self.assertFalse(self.approve_grant(variant_sha256="a"*64))
        self.assertTrue(self.approve_grant())
        self.assertFalse(self.approve_grant())
        self.assertIsNone(self.read(self.other))
        proof=self.read()
        self.assertEqual(proof.content,self.proof.content)
        self.assertIn(str(self.grant).encode(),proof.content)
        self.assertNotIn(str(self.owner).encode(),proof.content)
        self.assertIn(b"NOT FOR SALE",proof.content)
        self.assertIsNone(self.read(artwork=self.art+b"changed"))
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(self.read())
        self.assertTrue(revoke_session(self.dsn,self.tester))
        with self.assertRaises(PermissionError):
            self.read()

    def test_revocation_and_pause(self):
        self.assertTrue(self.approve_grant())
        self.store.set_paused(True)
        self.assertIsNone(self.read())
        self.store.set_paused(False)
        self.assertIsNotNone(self.read())
        self.assertTrue(revoke_beta(self.dsn,self.grant,reviewer_id=self.reviewer,
            evidence_ref="test:revoke",evidence=b"synthetic withdrawal",confirmed=True))
        self.assertIsNone(self.read())
        self.assertFalse(self.approve_grant())

    def test_preview_withdrawal(self):
        self.assertTrue(self.approve_grant())
        self.assertTrue(withdraw(self.dsn,self.preview,reviewer_id=self.reviewer,
            evidence_ref="test:withdraw",evidence=b"synthetic",confirmed=True))
        self.assertIsNone(self.read())

    def test_brand_revocation_and_expiry_validation(self):
        self.assertFalse(self.approve_grant(expires_at=int(time.time())+600))
        self.assertFalse(self.approve_grant(expires_at=int(time.time())-1))
        self.assertTrue(self.approve_grant())
        self.assertTrue(revoke(self.dsn,self.version,reviewer_id=self.reviewer,
            evidence_ref="test:revoke",evidence=b"synthetic",confirmed=True))
        self.assertIsNone(self.read())

    def test_new_quality_review_invalidates_exact_grant(self):
        self.assertTrue(self.approve_grant())
        self.assertIsNotNone(self.read())
        new=review(self.dsn,self.task,source_ref="test:beta-quality-new",
            expected_content_sha256=self.digest,checks={k:True for k in CRITERIA},
            revoked=False,reviewer_id=self.reviewer,evidence_ref="test:quality-new",
            evidence=b"new synthetic quality",confirmed=True)
        self.assertIsNotNone(new)
        self.assertNotEqual(new.entry_id,self.quality)
        self.assertIsNone(self.read())

    def test_access_after_expiry_uses_same_transaction_gate(self):
        from penny.scheduler.storage_db import locked
        self.assertTrue(self.approve_grant())
        self.assertIsNotNone(self.read())
        # Advance only the observed access time, not immutable grant rows.
        @contextmanager
        def after_expiry(dsn):
            with locked(dsn) as (conn,control,now):
                yield conn,control,self.args["expires_at"]
        with patch("penny.business.beta_access.locked",after_expiry):
            self.assertIsNone(self.read())
