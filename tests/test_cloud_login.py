"""Real login checks against isolated disposable PostgreSQL database."""
import unittest
from uuid import uuid4
from unittest.mock import patch

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from database_fixture import DSN
from netlify.security.login import inspect_connection,probe_login
from cloud_role_fixture import CloudRoleFixture


class LoginConfigTests(unittest.TestCase):
    @patch("netlify.security.login.psycopg.connect")
    def test_unverified_dsn_never_connects(self,connect):
        result=probe_login("host=db.example dbname=cloud user=reader password=fixture sslmode=require",
                           database="cloud",role="reader",scope="projection_reader")
        self.assertFalse(result.ready)
        connect.assert_not_called()


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class CloudLoginTests(CloudRoleFixture):
    def test_actual_login_detects_default_database_access_and_role_switch(self):
        role=self.roles["projection_reader"]
        password=uuid4().hex
        # Only create a login in the disposable database fixture.
        with psycopg.connect(DSN,autocommit=True) as admin:
            admin.execute(sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(role),sql.Literal(password)))
        dsn=make_conninfo(DSN,user=role,password=password,
                          options="-c search_path=pg_catalog,"+self.schema,sslmode="disable")
        with psycopg.connect(dsn) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            report=inspect_connection(conn,database="penny_test",schema=self.schema,
                role=role,scope="projection_reader",require_tls=False)
            # Shared CI DB grants PUBLIC TEMP by default. No global changes.
            self.assertIn("database_temp",report.issues)
            self.assertNotIn("wrong_runtime_login",report.issues)
            self.assertNotIn("unsafe_search_path",report.issues)
            self.assertIn("tls_required",inspect_connection(conn,database="penny_test",
                schema=self.schema,role=role,scope="projection_reader").issues)
        with psycopg.connect(DSN) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
            report=inspect_connection(conn,database="penny_test",schema=self.schema,
                role=role,scope="projection_reader",require_tls=False)
            self.assertIn("wrong_runtime_login",report.issues)

    def test_other_namespace_access_detected(self):
        role=self.roles["projection_reader"]
        other="other_"+uuid4().hex
        with psycopg.connect(DSN,autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(other)))
            try:
                admin.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                    sql.Identifier(other),sql.Identifier(role)))
                with psycopg.connect(DSN) as conn:
                    conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
                    report=inspect_connection(conn,database="penny_test",schema=self.schema,
                        role=role,scope="projection_reader",require_tls=False)
                    self.assertIn("other_application_schema_access",report.issues)
            finally:
                admin.execute(sql.SQL("DROP SCHEMA {}").format(sql.Identifier(other)))
