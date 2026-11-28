"""Disposable PostgreSQL only: projection role has routines, no raw table access."""
import unittest
from types import SimpleNamespace
from uuid import uuid4
import psycopg
from psycopg import sql
from database_fixture import DSN,DatabaseFixture
from penny.progress.delivery_gate import configure,binding
from penny.progress.activity import classify


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ProjectionScopeTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.role="projection_"+uuid4().hex
        self.addCleanup(self.remove_role)
        with psycopg.connect(self.dsn) as conn:
            role=sql.Identifier(self.role)
            conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(role))
            conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(self.schema),role))
            for signature in ("penny_activity_reserve(text)","penny_activity_finish(text)","penny_activity_inputs()"):
                conn.execute(sql.SQL("GRANT EXECUTE ON FUNCTION {} TO {}").format(sql.SQL(signature),role))
        self.cfg=SimpleNamespace(dsn=self.dsn,host="fixture.netlify.app",key=b"x"*32)

    def remove_role(self):
        with psycopg.connect(self.dsn) as conn:
            role=sql.Identifier(self.role)
            if conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s",(self.role,)).fetchone():
                conn.execute(sql.SQL("DROP OWNED BY {}").format(role))
                conn.execute(sql.SQL("DROP ROLE {}").format(role))

    def call(self,statement,args=()):
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(self.role)))
            return conn.execute(statement,args).fetchall()

    def test_only_fixed_routines_and_budget(self):
        key=binding(self.cfg)
        self.assertEqual(self.call("SELECT penny_activity_reserve(%s)",(key,)),[("paused",)])
        self.assertTrue(configure(self.cfg,enabled=True,limit=1,confirmed=True))
        self.assertEqual(self.call("SELECT penny_activity_reserve(%s)",("wrong",)),[("paused",)])
        self.assertEqual(self.call("SELECT penny_activity_reserve(%s)",(key,)),[("reserved",)])
        self.assertEqual(self.call("SELECT penny_activity_reserve(%s)",(key,)),[("review_required",)])
        self.assertEqual(len(self.call("SELECT * FROM penny_activity_inputs()")[0]),6)
        self.assertEqual(self.call("SELECT penny_activity_finish('published')"),[(True,)])
        self.assertEqual(self.call("SELECT penny_activity_finish('published')"),[(False,)])
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE activity_delivery_control SET not_before=0")
        self.assertEqual(self.call("SELECT penny_activity_reserve(%s)",(key,)),[("budget_exhausted",)])

    def test_no_raw_reads_or_privileged_writes(self):
        for statement in ("SELECT payload FROM work_task",
                          "SELECT result FROM task_outcome",
                          "SELECT * FROM activity_delivery_control",
                          "SELECT * FROM activity_delivery_review",
                          "UPDATE scheduler_control SET paused=false",
                          "UPDATE activity_delivery_control SET daily_limit=1440",
                          "UPDATE inference_runtime SET enabled=true"):
            with self.subTest(statement=statement):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    self.call(statement)


class ActivityClassificationTests(unittest.TestCase):
    def test_paused_active_is_not_reported_as_stopped(self):
        result=classify({"paused":True,"rest_enabled":False},
                        {"enabled":False,"uncertain":True},1050,1000)
        self.assertEqual(result["state"],"draining")
        result=classify({"paused":True,"rest_enabled":False},
                        {"enabled":False,"uncertain":True},None,1000)
        self.assertEqual(result["state"],"blocked")
