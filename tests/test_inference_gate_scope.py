"""Inference gate fencing; disposable PostgreSQL only."""
import unittest
from uuid import uuid4
from unittest.mock import Mock,patch

import psycopg
from psycopg import sql
from database_fixture import DSN,DatabaseFixture
from penny.runtime.inference_db import gate_call
from penny.runtime.operator_control import stop,recover_inference


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class InferenceGateScopeTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET enabled=true")

    def test_fenced_once_and_sticky_failure(self):
        first=gate_call(self.dsn,"begin")
        self.assertEqual(first["status"],"reserved")
        token=first["token"]
        self.assertEqual(gate_call(self.dsn,"begin")["status"],"blocked")
        self.assertEqual(gate_call(self.dsn,"finish",(uuid4(),"idle"))["status"],"blocked")
        self.assertEqual(gate_call(self.dsn,"finish",(token,"idle"))["status"],"idle")
        second=gate_call(self.dsn,"begin")
        self.assertEqual(second["status"],"reserved")
        self.assertNotEqual(token,second["token"])
        self.assertEqual(gate_call(self.dsn,"finish",(token,"idle"))["status"],"blocked")
        self.assertEqual(gate_call(self.dsn,"finish",(second["token"],"blocked"))["status"],"blocked")
        self.assertEqual(gate_call(self.dsn,"begin")["status"],"blocked")
        self.assertEqual(gate_call(self.dsn,"finish",(second["token"],"idle"))["status"],"blocked")

    def test_active_task_prevents_clear(self):
        reservation=gate_call(self.dsn,"begin")
        self.store.submit(None,"work","Work")
        self.assertIsNotNone(self.store.claim())
        self.assertEqual(gate_call(self.dsn,"finish",(reservation["token"],"completed"))["status"],"blocked")
        self.assertEqual(gate_call(self.dsn,"begin")["status"],"blocked")

    def test_maker_recovery_invalidates_old_cycle(self):
        reservation=gate_call(self.dsn,"begin")
        stop(self.dsn)
        self.assertTrue(recover_inference(self.dsn,isolated=True))
        self.assertEqual(gate_call(self.dsn,"finish",(reservation["token"],"idle"))["status"],"blocked")
        self.assertEqual(gate_call(self.dsn,"begin")["status"],"paused")

    def test_restricted_gate_cannot_modify_or_read_private_tables(self):
        role=sql.Identifier("inf_gate_"+uuid4().hex)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(role))
            conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(self.schema),role))
            for signature in ("penny_inference_begin()","penny_inference_finish(uuid,text)"):
                conn.execute(sql.SQL("GRANT EXECUTE ON FUNCTION {} TO {}").format(sql.SQL(signature),role))

        def cleanup():
            with psycopg.connect(self.dsn) as conn:
                conn.execute(sql.SQL("DROP OWNED BY {}").format(role))
                conn.execute(sql.SQL("DROP ROLE {}").format(role))

        self.addCleanup(cleanup)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(role))
            status,token=conn.execute("SELECT * FROM penny_inference_begin()").fetchone()
            self.assertEqual(status,"reserved")
            for statement in ("UPDATE inference_runtime SET enabled=true",
                              "UPDATE inference_runtime SET uncertain=false",
                              "UPDATE scheduler_control SET paused=false",
                              "SELECT payload FROM work_task",
                              "SELECT * FROM penny_activity_inputs()",
                              "SELECT * FROM penny_bridge_reserve()"):
                with self.subTest(statement=statement),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute(statement)
            self.assertEqual(conn.execute("SELECT penny_inference_finish(%s,'idle')",(token,)).fetchone()[0],"idle")
