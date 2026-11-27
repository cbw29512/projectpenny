"""Dedicated role provisioning on disposable PostgreSQL only."""
import unittest
from uuid import uuid4
from pathlib import Path

import psycopg
from psycopg import sql
from database_fixture import DSN
from penny.runtime.role_state import SCOPES
from penny.runtime.role_audit import audit_role
from penny.runtime.role_provision import configure_roles


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class LocalRolesTests(unittest.TestCase):
    def setUp(self):
        suffix=uuid4().hex
        self.schema="local_"+suffix
        self.owner="owner_"+suffix
        self.roles={scope:scope+"_"+suffix for scope in SCOPES}
        self.addCleanup(self.cleanup)
        with psycopg.connect(DSN,autocommit=True) as conn:
            if conn.info.dbname!="penny_test":
                raise RuntimeError("disposable DB required")
            for role in (self.owner,*self.roles.values()):
                conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(role)))
            conn.execute(sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
                sql.Identifier(self.schema),sql.Identifier(self.owner)))
            self.as_owner(conn)
            for path in sorted(Path("migrations").glob("*.sql")):
                conn.execute(path.read_text())

    def as_owner(self,conn):
        conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(self.owner)))
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))

    def cleanup(self):
        with psycopg.connect(DSN,autocommit=True) as conn:
            if conn.info.dbname!="penny_test":
                raise RuntimeError("disposable DB required")
            conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema)))
            for role in (*self.roles.values(),self.owner):
                conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))

    def configure(self,conn):
        self.as_owner(conn)
        return configure_roles(conn,self.schema,**self.roles,confirmed=True)

    def test_exact_scopes_and_cross_service_denial(self):
        with psycopg.connect(DSN) as conn:
            reports=self.configure(conn)
            self.assertTrue(all(r.ready for r in reports.values()))
            self.assertTrue(all(audit_role(conn,self.schema,role,scope).ready
                                for scope,role in self.roles.items()))
        for scope,role in self.roles.items():
            with psycopg.connect(DSN) as conn:
                conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
                for statement in ("SELECT * FROM work_task","SELECT * FROM member_memory",
                                  "UPDATE scheduler_control SET paused=false",
                                  "SELECT * FROM penny_private_parse_maintenance('{}')"):
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege),conn.transaction():
                        conn.execute(statement)
                for other,sigs in SCOPES.items():
                    for sig in sigs:
                        self.assertEqual(conn.execute(
                            "SELECT has_function_privilege(current_user,%s,'EXECUTE')",
                            (self.schema+"."+sig,)).fetchone()[0],scope==other)

    def test_existing_column_grant_rolls_back_new_permissions(self):
        with psycopg.connect(DSN) as conn:
            self.as_owner(conn)
            conn.execute(sql.SQL("GRANT SELECT(payload) ON work_task TO {}").format(
                sql.Identifier(self.roles["inference"])))
            with self.assertRaises(PermissionError):
                configure_roles(conn,self.schema,**self.roles,confirmed=True)
            report=audit_role(conn,self.schema,self.roles["inference"],"inference")
            self.assertIn("direct_relation:work_task",report.issues)
            self.assertIn("missing_execute:penny_inference_begin",report.issues)
            self.assertIn("missing_schema_usage",report.issues)

    def test_owner_confirmation_and_schema_requirements(self):
        with psycopg.connect(DSN) as conn:
            with self.assertRaises(PermissionError):
                configure_roles(conn,self.schema,**self.roles,confirmed=True)
            self.as_owner(conn)
            with self.assertRaises(ValueError):
                configure_roles(conn,self.schema,**self.roles)
            with self.assertRaises(ValueError):
                configure_roles(conn,"public",**self.roles,confirmed=True)

    def test_audit_detects_cross_scope_and_definer_drift(self):
        with psycopg.connect(DSN) as conn:
            self.configure(conn)
            conn.execute(sql.SQL("GRANT EXECUTE ON FUNCTION penny_activity_inputs() TO {}").format(
                sql.Identifier(self.roles["inference"])))
            conn.execute("ALTER FUNCTION penny_inference_begin() SET search_path TO public")
            report=audit_role(conn,self.schema,self.roles["inference"],"inference")
            self.assertIn("excess_routine:penny_activity_inputs",report.issues)
            self.assertIn("unsafe_routine:penny_inference_begin",report.issues)
