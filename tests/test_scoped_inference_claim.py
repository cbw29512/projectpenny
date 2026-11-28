"""Disposable DB: scoped claim parity and restricted role boundary."""
import unittest
from uuid import uuid4

import psycopg
from psycopg import sql
from database_fixture import DSN,DatabaseFixture
from penny.runtime.claim_store import ScopedClaimStore
from penny.runtime.inference_db import gate_call
from penny.scheduler.policy import next_task
from penny.scheduler.storage_db import locked,snapshot
from penny.scheduler.outcomes import complete


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ScopedClaimTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET enabled=true")

    def reserve(self):
        row=gate_call(self.dsn,"begin")
        self.assertEqual(row["status"],"reserved")
        return row["token"]

    def test_matches_existing_dispatch_with_measured_usage_and_age(self):
        member=uuid4()
        self.assertEqual(self.store.submit(None,"business","Business").status,"accept")
        self.assertEqual(self.store.submit(member,"visitor","Question").status,"accept")
        for _ in range(2):
            token=self.reserve()
            with locked(self.dsn) as (conn,control,now):
                expected=next_task(snapshot(conn,control,now),now)
            claim=ScopedClaimStore(self.dsn,token).claim()
            self.assertEqual(str(claim.task_id),expected.task_id)
            self.assertTrue(complete(self.dsn,claim.task_id,claim.fence,success=True,result="Draft"))
            self.assertEqual(gate_call(self.dsn,"finish",(token,"completed"))["status"],"completed")
        token=self.reserve()
        self.assertIsNone(ScopedClaimStore(self.dsn,token).claim())
        with self.assertRaises(psycopg.Error):
            ScopedClaimStore(self.dsn,token).claim()

    def test_aged_visitor_overrides_business_priority(self):
        member=uuid4()
        old=self.store.submit(member,"old","Older")
        self.store.submit(None,"new","Business")
        with locked(self.dsn) as (conn,control,now):
            conn.execute("UPDATE work_task SET submitted_at=%s WHERE id=%s",(now-901,old.task_id))
            expected=next_task(snapshot(conn,control,now),now)
        self.assertEqual(expected.task_id,str(old.task_id))
        self.assertEqual(ScopedClaimStore(self.dsn,self.reserve()).claim().task_id,old.task_id)

    def test_pause_and_entitlement_change(self):
        member=uuid4()
        task=self.store.submit(member,"visitor","Question")
        with psycopg.connect(self.dsn) as conn:
            conn.execute("INSERT INTO scheduler_entitlement VALUES (%s,1,9999999999)",(member,))
        token=self.reserve()
        self.assertIsNone(ScopedClaimStore(self.dsn,token).claim())
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT state FROM work_task WHERE id=%s",(task.task_id,)).fetchone()[0],"canceled")
        self.assertEqual(gate_call(self.dsn,"finish",(token,"idle"))["status"],"idle")
        token=self.reserve()
        self.store.submit(None,"work","Work")
        self.store.set_paused(True)
        self.assertIsNone(ScopedClaimStore(self.dsn,token).claim())

    def test_role_can_claim_only_reserved_task(self):
        role=sql.Identifier("claim_"+uuid4().hex)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(role))
            conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(self.schema),role))
            conn.execute(sql.SQL("GRANT EXECUTE ON FUNCTION penny_inference_claim(uuid) TO {}").format(role))

        def cleanup():
            with psycopg.connect(self.dsn) as conn:
                conn.execute(sql.SQL("DROP OWNED BY {}").format(role))
                conn.execute(sql.SQL("DROP ROLE {}").format(role))

        self.addCleanup(cleanup)
        self.store.submit(None,"one","Private task")
        token=self.reserve()
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(role))
            with self.assertRaises(psycopg.Error):
                with conn.transaction():
                    conn.execute("SELECT * FROM penny_inference_claim(%s)",(uuid4(),))
            row=conn.execute("SELECT * FROM penny_inference_claim(%s)",(token,)).fetchone()
            self.assertEqual(row[2],"Private task")
            for statement in ("SELECT payload FROM work_task","SELECT * FROM task_outcome",
                              "UPDATE scheduler_control SET paused=false",
                              "UPDATE inference_runtime SET enabled=true",
                              "SELECT * FROM penny_bridge_reserve()"):
                with self.subTest(statement=statement),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute(statement)
            with self.assertRaises(psycopg.Error):
                with conn.transaction():
                    conn.execute("SELECT * FROM penny_inference_claim(%s)",(token,))
