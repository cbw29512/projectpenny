"""End-to-end mailbox with EXECUTE-only role on disposable PostgreSQL."""
from datetime import datetime,timedelta,timezone
import unittest
from unittest.mock import Mock
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from database_fixture import DSN,DatabaseFixture
from penny.bridge.state import RemoteClaim,BridgeResult
from penny.bridge.worker import run_bridge_once
from penny.bridge.release import approve_reply
from penny.scheduler.outcomes import complete

SIGNATURES=("penny_bridge_admit(uuid,uuid,uuid,bigint,text)",
            "penny_bridge_ack(uuid,uuid,uuid)",
            "penny_bridge_pending_reply(uuid)",
            "penny_bridge_record_delivery(uuid,uuid,text)",
            "penny_bridge_reserve()","penny_bridge_defer(integer,text)",
            "penny_bridge_reject(uuid,uuid,uuid)")


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class MailboxRoleTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.role="mailbox_"+uuid4().hex
        ident=sql.Identifier(self.role)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(ident))
            conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(self.schema),ident))
            for signature in SIGNATURES:
                conn.execute(sql.SQL("GRANT EXECUTE ON FUNCTION {} TO {}").format(
                    sql.SQL(signature),ident))
            self.owner,self.member=uuid4(),uuid4()
            conn.execute("INSERT INTO bridge_member VALUES (%s,%s,true)",(self.owner,self.member))
            conn.execute("UPDATE bridge_control SET enabled=true")
        self.addCleanup(self.remove_role)
        # Test-only SET ROLE at connection startup. Production uses a
        # dedicated authenticated login, not an owner connection.
        self.worker_dsn=make_conninfo(self.dsn,options=
            "-c search_path="+self.schema+" -c role="+self.role)
        self.client=Mock()
        self.remote=RemoteClaim(uuid4(),self.owner,uuid4(),
            datetime.now(timezone.utc)+timedelta(minutes=10),"Question")
        self.client.claim.return_value=BridgeResult("claimed",self.remote)
        self.client.ack.return_value=BridgeResult("ok")
        self.client.answer.return_value=BridgeResult("ok")
        self.client.reject.return_value=BridgeResult("ok")

    def remove_role(self):
        with psycopg.connect(self.dsn) as conn:
            ident=sql.Identifier(self.role)
            conn.execute(sql.SQL("DROP OWNED BY {}").format(ident))
            conn.execute(sql.SQL("DROP ROLE {}").format(ident))

    def tick(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE bridge_control SET not_before=0")
        return run_bridge_once(self.worker_dsn,self.client).status

    def test_reviewed_delivery_roundtrip(self):
        self.assertEqual(self.tick(),"admitted")
        self.assertEqual(self.tick(),"acknowledged")
        task=self.store.claim()
        self.assertTrue(complete(self.dsn,task.task_id,task.fence,success=True,result="Draft"))
        self.assertEqual(self.tick(),"waiting_review")
        self.client.answer.assert_not_called()
        self.assertTrue(approve_reply(self.dsn,self.remote.id,
            reviewer_id=uuid4(),expected_text="Draft"))
        self.assertEqual(self.tick(),"delivered")
        self.client.answer.assert_called_once_with(self.remote.id,self.remote.fence,"Draft")

    def test_failed_work_and_sticky_block(self):
        self.assertEqual(self.tick(),"admitted")
        self.assertEqual(self.tick(),"acknowledged")
        task=self.store.claim()
        self.assertTrue(complete(self.dsn,task.task_id,task.fence,success=False,result="Failed"))
        self.assertEqual(self.tick(),"rejected")
        self.client.claim.return_value=BridgeResult("unauthorized")
        self.assertEqual(self.tick(),"blocked")
        self.assertEqual(self.tick(),"paused")

    def test_no_raw_access_or_other_worker_routines(self):
        for statement in ("SELECT payload FROM work_task",
                          "SELECT result FROM task_outcome",
                          "UPDATE bridge_control SET not_before=0",
                          "UPDATE bridge_control SET blocked_reason=NULL",
                          "UPDATE scheduler_control SET paused=false",
                          "INSERT INTO bridge_release SELECT * FROM bridge_release",
                          "SELECT * FROM penny_activity_inputs()",
                          "SELECT penny_bridge_rest_closed(true,0)"):
            with self.subTest(statement=statement):
                with psycopg.connect(self.worker_dsn) as conn:
                    self.assertEqual(conn.execute("SELECT current_user").fetchone()[0],self.role)
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        with conn.transaction():
                            conn.execute(statement)
        with psycopg.connect(self.worker_dsn) as conn:
            self.assertFalse(conn.execute("SELECT penny_bridge_defer(0,NULL)").fetchone()[0])

    def test_database_rest_boundaries(self):
        for when,expected in (("2026-11-26T23:59:59-05:00",False),
                              ("2026-11-27T00:00:00-05:00",True),
                              ("2026-11-27T07:59:59-05:00",True),
                              ("2026-11-27T08:00:00-05:00",False),
                              ("2026-03-08T07:59:59-04:00",True),
                              ("2026-11-01T08:00:00-05:00",False)):
            epoch=int(datetime.fromisoformat(when).timestamp())
            with psycopg.connect(self.dsn) as conn:
                self.assertEqual(conn.execute("SELECT penny_bridge_rest_closed(true,%s)",
                    (epoch,)).fetchone()[0],expected)
