"""Effective grants preflight on disposable PostgreSQL, never production."""
import unittest

from psycopg import sql
from database_fixture import DSN
from cloud_role_fixture import CloudRoleFixture
from netlify.security.audit import audit_role


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class CloudAuditTests(CloudRoleFixture):
    def audit(self,scope="member"):
        import psycopg
        with psycopg.connect(DSN) as conn:
            return audit_role(conn,self.schema,self.roles[scope],scope)

    def ddl(self,statement):
        import psycopg
        with psycopg.connect(DSN) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(self.roles["owner"])))
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
            conn.execute(statement)

    def grant(self,statement,role="member"):
        self.ddl(sql.SQL(statement).format(sql.Identifier(self.roles[role])))

    def test_all_scopes_pass_clean_fixture(self):
        for scope in ("member","bridge","maintenance","admin"):
            result=self.audit(scope)
            self.assertTrue(result.ready,result.issues)

    def test_column_grant_detected(self):
        self.grant("GRANT SELECT(body) ON mailbox_question TO {}")
        self.assertIn("direct_relation:mailbox_question",self.audit().issues)

    def test_public_grant_detected(self):
        self.ddl("GRANT SELECT ON mailbox_member TO PUBLIC")
        self.assertIn("direct_relation:mailbox_member",self.audit().issues)

    def test_excess_and_missing_routine_detected(self):
        self.grant("GRANT EXECUTE ON FUNCTION mailbox_claim() TO {}")
        self.grant("REVOKE EXECUTE ON FUNCTION mailbox_submit(uuid,uuid,text) FROM {}")
        result=self.audit()
        self.assertIn("excess_routine:mailbox_claim",result.issues)
        self.assertIn("missing_execute:mailbox_submit",result.issues)

    def test_search_path_drift_detected(self):
        self.ddl("ALTER FUNCTION mailbox_read(uuid,uuid) SET search_path TO public")
        self.assertIn("unsafe_routine:mailbox_read",self.audit().issues)

    def test_grant_option_detected(self):
        self.grant("GRANT EXECUTE ON FUNCTION mailbox_read(uuid,uuid) TO {} WITH GRANT OPTION")
        self.assertIn("excess_routine:mailbox_read",self.audit().issues)
