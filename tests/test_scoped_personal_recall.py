"""Scoped personal recall: disposable PostgreSQL, no external model."""
import unittest
from unittest.mock import Mock
from uuid import uuid4

import psycopg
from psycopg import sql
from database_fixture import DSN,DatabaseFixture
from penny.auth.member_chat import MemberChatService
from penny.auth.member_memory import MemberMemoryService
from penny.auth.session import issue_session
from penny.memory.member_state import CONSENT_VERSION
from penny.runtime.claim_store import ScopedClaimStore
from penny.runtime.inference_db import gate_call
from penny.runtime.personal_recall import ScopedPersonalRecall
from penny.runtime.inference import inference_tick
from penny.scheduler.outcomes import complete


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ScopedPersonalTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.chat=MemberChatService(self.store)
        self.memory=MemberMemoryService(self.dsn)
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET enabled=true")

    def member(self):
        session=issue_session(self.dsn,uuid4())
        consent=self.memory.opt_in(session.token,accepted_version=CONSENT_VERSION)
        return session,consent

    def claim(self):
        row=gate_call(self.dsn,"begin")
        self.assertEqual(row["status"],"reserved")
        return row["token"],ScopedClaimStore(self.dsn,row["token"]).claim()

    def test_supervised_worker_receives_only_owner_preferences(self):
        a,ca=self.member()
        b,cb=self.member()
        item=self.memory.save(a.token,ca.epoch,"Concise replies")
        self.memory.save(b.token,cb.epoch,"Other member")
        self.chat.submit(a.token,"a","Question",use_personal_memory=True)
        brain=Mock()
        brain.generate_with_preferences.return_value="Draft"
        self.assertEqual(inference_tick(self.dsn,brain),"completed")
        self.assertEqual(brain.generate_with_preferences.call_args.args[2],(item,))
        brain.generate_with_memory.assert_not_called()

    def test_fence_and_deletion_after_recall(self):
        a,ca=self.member()
        item=self.memory.save(a.token,ca.epoch,"Private preference")
        self.chat.submit(a.token,"a","Question",use_personal_memory=True)
        token,claim=self.claim()
        reader=ScopedPersonalRecall(token)
        self.assertEqual(reader(self.dsn,claim.task_id,uuid4()),())
        self.assertEqual(reader(self.dsn,claim.task_id,claim.fence),(item,))
        with self.assertRaises(psycopg.Error):
            reader(self.dsn,claim.task_id,claim.fence)
        self.assertTrue(self.memory.delete(a.token,item.id))
        self.assertFalse(complete(self.dsn,claim.task_id,claim.fence,
                                  success=True,result="Private preference"))

    def test_empty_attempt_consumed_and_stale_consent(self):
        a,ca=self.member()
        self.chat.submit(a.token,"a","Question",use_personal_memory=True)
        self.memory.withdraw(a.token)
        renewed=self.memory.opt_in(a.token,accepted_version=CONSENT_VERSION)
        self.memory.save(a.token,renewed.epoch,"New epoch")
        token,claim=self.claim()
        reader=ScopedPersonalRecall(token)
        self.assertEqual(reader(self.dsn,claim.task_id,claim.fence),())
        with self.assertRaises(psycopg.Error):
            reader(self.dsn,claim.task_id,claim.fence)

    def test_restricted_role_cannot_browse_or_change_memory(self):
        a,ca=self.member()
        self.memory.save(a.token,ca.epoch,"Allowed")
        self.chat.submit(a.token,"a","Question",use_personal_memory=True)
        token,claim=self.claim()
        role=sql.Identifier("personal_"+uuid4().hex)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(role))
            conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(self.schema),role))
            conn.execute(sql.SQL("GRANT EXECUTE ON FUNCTION penny_inference_personal_recall(uuid,uuid,uuid) TO {}").format(role))

        def cleanup():
            with psycopg.connect(self.dsn) as conn:
                conn.execute(sql.SQL("DROP OWNED BY {}").format(role))
                conn.execute(sql.SQL("DROP ROLE {}").format(role))
        self.addCleanup(cleanup)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(role))
            with self.assertRaises(psycopg.Error):
                with conn.transaction():
                    conn.execute("SELECT * FROM penny_inference_personal_recall(%s,%s,%s)",
                                 (uuid4(),claim.task_id,claim.fence))
            self.assertEqual(conn.execute("SELECT * FROM penny_inference_personal_recall(%s,%s,%s)",
                                          (token,claim.task_id,claim.fence)).fetchone()[1],"Allowed")
            for statement in ("SELECT * FROM member_memory","SELECT * FROM business_memory",
                              "UPDATE member_memory_consent SET enabled=true",
                              "DELETE FROM member_recall_snapshot",
                              "DELETE FROM inference_personal_recall_attempt"):
                with self.subTest(statement=statement),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute(statement)
