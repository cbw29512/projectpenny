"""Scoped completion tests on disposable PostgreSQL only."""
import unittest
from uuid import uuid4
from unittest.mock import patch,Mock

import psycopg
from psycopg import sql
from database_fixture import DSN,DatabaseFixture
from penny.runtime.claim_store import ScopedClaimStore
from penny.runtime.inference_db import gate_call
from penny.runtime.draft_completion import ScopedDraftCompletion
from penny.runtime.personal_recall import ScopedPersonalRecall
from penny.runtime.inference import inference_tick
from penny.auth.member_chat import MemberChatService
from penny.auth.member_memory import MemberMemoryService
from penny.auth.session import issue_session
from penny.memory.member_state import CONSENT_VERSION
from penny.memory.intake import submit_review


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class DraftCompletionTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET enabled=true")

    def reserve(self):
        r=gate_call(self.dsn,"begin")
        self.assertEqual(r["status"],"reserved")
        return r["token"],ScopedClaimStore(self.dsn,r["token"]).claim()

    def test_fenced_completion_is_single_use(self):
        self.store.submit(None,"ordinary","Draft a plan")
        token,claim=self.reserve()
        complete=ScopedDraftCompletion(token)
        self.assertFalse(complete(self.dsn,claim.task_id,uuid4(),success=True,result="Draft"))
        self.assertFalse(ScopedDraftCompletion(uuid4())(self.dsn,claim.task_id,claim.fence,success=True,result="Draft"))
        self.assertTrue(complete(self.dsn,claim.task_id,claim.fence,success=True,result="Draft"))
        self.assertFalse(complete(self.dsn,claim.task_id,claim.fence,success=True,result="Replacement"))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT status,result FROM task_outcome").fetchall(),
                             [("succeeded","Draft")])

    def test_revoked_preference_never_stored(self):
        s=issue_session(self.dsn,uuid4())
        memory=MemberMemoryService(self.dsn)
        c=memory.opt_in(s.token,accepted_version=CONSENT_VERSION)
        item=memory.save(s.token,c.epoch,"Private preference")
        MemberChatService(self.store).submit(s.token,"a","Question",use_personal_memory=True)
        token,claim=self.reserve()
        self.assertEqual(ScopedPersonalRecall(token)(self.dsn,claim.task_id,claim.fence),(item,))
        self.assertTrue(memory.delete(s.token,item.id))
        self.assertFalse(ScopedDraftCompletion(token)(self.dsn,claim.task_id,claim.fence,
                         success=True,result="Private preference"))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT status,result FROM task_outcome").fetchall(),
                             [("canceled","personal memory permission changed")])

    def test_learning_candidate_is_scoped_and_atomic(self):
        submit_review(self.store,"lesson","Observed result")
        token,claim=self.reserve()
        result='{"kind":"lesson","content":"Measure first"}'
        self.assertTrue(ScopedDraftCompletion(token)(self.dsn,claim.task_id,claim.fence,
                         success=True,result=result))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT content,validation_state FROM memory_candidate").fetchall(),
                             [("Measure first","quarantined")])
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory").fetchone()[0],0)

    def test_other_specialized_route_still_refused_without_legacy(self):
        from penny.memory.maintenance import submit_maintenance
        submit_maintenance(self.store,"lesson","Observed result")
        token,claim=self.reserve()
        self.assertFalse(ScopedDraftCompletion(token)(self.dsn,claim.task_id,claim.fence,
                         success=True,result="{}"))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM task_outcome").fetchone()[0],0)

    def test_restricted_role_cannot_overwrite_outcome(self):
        self.store.submit(None,"ordinary","Draft a plan")
        token,claim=self.reserve()
        role=sql.Identifier("draft_"+uuid4().hex)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(role))
            conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(self.schema),role))
            conn.execute(sql.SQL("GRANT EXECUTE ON FUNCTION penny_inference_complete_draft(uuid,uuid,uuid,text) TO {}").format(role))

        def cleanup():
            with psycopg.connect(self.dsn) as conn:
                conn.execute(sql.SQL("DROP OWNED BY {}").format(role))
                conn.execute(sql.SQL("DROP ROLE {}").format(role))
        self.addCleanup(cleanup)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(role))
            self.assertEqual(conn.execute("SELECT penny_inference_complete_draft(%s,%s,%s,%s)",
                (token,claim.task_id,claim.fence,"Draft")).fetchone()[0],"completed")
            for statement in ("UPDATE task_outcome SET result='Forged'",
                              "UPDATE work_task SET state='queued'",
                              "INSERT INTO bridge_release SELECT * FROM bridge_release",
                              "INSERT INTO business_memory SELECT * FROM business_memory"):
                with self.subTest(statement=statement),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute(statement)
