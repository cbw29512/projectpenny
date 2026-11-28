"""Session ownership tests using disposable PostgreSQL."""
import hashlib
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from memory_review_fixture import DSN, ReviewFixture
from penny.auth.member_memory import MemberMemoryService
from penny.auth.session import issue_session, revoke_session
from penny.auth.state import MAX_ACTIVE_SESSIONS
from penny.memory.member_state import CONSENT_VERSION


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class SessionTests(ReviewFixture):
    def setUp(self):
        super().setUp()
        self.service = MemberMemoryService(self.dsn)

    def session(self, member=None):
        return issue_session(self.dsn,member or uuid4())

    def enable(self, session):
        return self.service.opt_in(session.token,accepted_version=CONSENT_VERSION)

    def test_token_is_random_and_only_digest_stored(self):
        s = self.session()
        self.assertEqual(len(s.token),43)
        self.assertNotIn(s.token,repr(s))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT token_sha256 FROM member_session").fetchone()[0],
                             hashlib.sha256(s.token.encode("ascii")).hexdigest())

    def test_token_owner_cannot_read_write_or_delete_other_preferences(self):
        a,b = self.session(),self.session()
        ca,cb = self.enable(a),self.enable(b)
        item = self.service.save(a.token,ca.epoch,"Concise replies")
        self.assertEqual(self.service.list(b.token),())
        self.assertIsNone(self.service.save(b.token,ca.epoch,"forged"))
        self.assertFalse(self.service.delete(b.token,item.id))
        self.assertEqual(self.service.list(a.token),(item,))
        self.assertTrue(self.service.withdraw(b.token))
        self.assertEqual(self.service.list(a.token),(item,))
        self.assertIsNotNone(cb)

    def test_revocation_blocks_operations(self):
        s = self.session()
        c = self.enable(s)
        self.assertTrue(revoke_session(self.dsn,s.token))
        self.assertFalse(revoke_session(self.dsn,s.token))
        for operation in (lambda:self.service.list(s.token),
                          lambda:self.service.save(s.token,c.epoch,"stale"),
                          lambda:self.service.withdraw(s.token)):
            with self.assertRaises(PermissionError):
                operation()

    def test_expired_and_unknown_session(self):
        s = self.session()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE member_session SET issued_at=1,expires_at=2")
        for token in (s.token,"a"*43,None,uuid4(),""):
            with self.assertRaises(PermissionError):
                self.service.list(token)

    def test_session_cap_and_identity_failure(self):
        member = uuid4()
        sessions = [self.session(member) for _ in range(MAX_ACTIVE_SESSIONS)]
        self.assertIsNone(self.session(member))
        self.assertTrue(revoke_session(self.dsn,sessions[0].token))
        s = self.session(member)
        self.assertIsNotNone(s)
        self.enable(s)
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertIsNone(self.session())
            self.assertTrue(self.service.withdraw(s.token))
            self.assertTrue(revoke_session(self.dsn,s.token))
