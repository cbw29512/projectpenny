"""Disposable database tests for explicit, scoped member memory."""
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from memory_review_fixture import DSN, ReviewFixture
from penny.memory.member_consent import opt_in, withdraw
from penny.memory.member_preferences import save_preference, list_preferences, delete_preference
from penny.memory.member_state import CONSENT_VERSION, MAX_MEMBER_MEMORIES


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class MemberMemoryTests(ReviewFixture):
    def enable(self, member):
        return opt_in(self.dsn,member,accepted_version=CONSENT_VERSION)

    def test_default_off_and_explicit_version(self):
        member = uuid4()
        self.assertEqual(list_preferences(self.dsn,member),())
        self.assertIsNone(save_preference(self.dsn,member,uuid4(),"Use concise replies"))
        with self.assertRaises(ValueError):
            opt_in(self.dsn,member,accepted_version="old")
        consent = self.enable(member)
        self.assertEqual(self.enable(member),consent)

    def test_owner_and_epoch_isolation(self):
        a,b = uuid4(),uuid4()
        ca,cb = self.enable(a),self.enable(b)
        item = save_preference(self.dsn,a,ca.epoch,"Use concise replies")
        self.assertIsNotNone(item)
        self.assertEqual(list_preferences(self.dsn,b),())
        self.assertIsNone(save_preference(self.dsn,b,ca.epoch,"forged"))
        self.assertFalse(delete_preference(self.dsn,b,item.id))
        self.assertEqual(list_preferences(self.dsn,a),(item,))
        self.assertEqual(save_preference(self.dsn,a,ca.epoch,"Use concise replies"),item)
        self.assertTrue(delete_preference(self.dsn,a,item.id))
        self.assertEqual(list_preferences(self.dsn,a),())
        self.assertIsNotNone(cb)

    def test_withdrawal_does_not_resurrect_or_depend_on_identity(self):
        member = uuid4()
        old = self.enable(member)
        save_preference(self.dsn,member,old.epoch,"Use short answers")
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertTrue(withdraw(self.dsn,member))
        self.assertFalse(withdraw(self.dsn,member))
        new = self.enable(member)
        self.assertNotEqual(old.epoch,new.epoch)
        self.assertEqual(list_preferences(self.dsn,member),())
        self.assertIsNone(save_preference(self.dsn,member,old.epoch,"stale"))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM member_memory").fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT count(*) FROM member_memory_consent_event").fetchone()[0],3)

    def test_expired_consent_blocks_reads_and_writes(self):
        member = uuid4()
        old = self.enable(member)
        save_preference(self.dsn,member,old.epoch,"A preference")
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE member_memory_consent SET granted_at=1,expires_at=2")
        self.assertEqual(list_preferences(self.dsn,member),())
        self.assertIsNone(save_preference(self.dsn,member,old.epoch,"another"))
        new = self.enable(member)
        self.assertNotEqual(old.epoch,new.epoch)
        self.assertEqual(list_preferences(self.dsn,member),())

    def test_bounded_storage(self):
        member = uuid4()
        consent = self.enable(member)
        for i in range(MAX_MEMBER_MEMORIES):
            self.assertIsNotNone(save_preference(self.dsn,member,consent.epoch,str(i)))
        self.assertIsNone(save_preference(self.dsn,member,consent.epoch,"extra"))
        with self.assertRaises(ValueError):
            save_preference(self.dsn,member,consent.epoch,"x"*301)

    def test_audit_failure_rolls_back_withdrawal(self):
        member = uuid4()
        consent = self.enable(member)
        item = save_preference(self.dsn,member,consent.epoch,"A preference")
        with psycopg.connect(self.dsn) as conn:
            conn.execute("DROP TABLE member_memory_consent_event")
        with self.assertRaises(psycopg.Error):
            withdraw(self.dsn,member)
        self.assertEqual(list_preferences(self.dsn,member),(item,))
