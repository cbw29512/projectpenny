"""Restricted completion grants must not confer commercial authority."""
import unittest
from uuid import uuid4
import psycopg
from psycopg import sql
import test_scoped_revenue as fixture
from database_fixture import DSN


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ScopedProductRoleTests(fixture.ScopedRevenueTests):
    def test_restricted_workshop_completion_and_denied_authority(self):
        r=self.workshop()
        from penny.runtime.inference_db import gate_call
        from penny.runtime.claim_store import ScopedClaimStore
        token=gate_call(self.dsn,"begin")["token"]
        claim=ScopedClaimStore(self.dsn,token).claim()
        role=sql.Identifier("product_"+uuid4().hex)
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
                (token,claim.task_id,claim.fence,fixture.RAW)).fetchone()[0],"completed")
            for statement in ("INSERT INTO business_opportunity SELECT * FROM business_opportunity",
                              # PostgreSQL rejects explicit GENERATED ALWAYS values
                              # before checking permissions. Omit the identity column
                              # and use an empty source: the statement is valid but
                              # must still fail with insufficient privilege.
                              "INSERT INTO business_experiment_event "
                              "(id,opportunity_id,action,reviewer_id,recorded_at,deadline,"
                              "observed_at,measured_count,evidence_ref,evidence_sha256,"
                              "evidence_size,policy_version) "
                              "SELECT id,opportunity_id,action,reviewer_id,recorded_at,deadline,"
                              "observed_at,measured_count,evidence_ref,evidence_sha256,"
                              "evidence_size,policy_version FROM business_experiment_event WHERE false",
                              "UPDATE workshop_artifact SET content='Forged'",
                              "INSERT INTO vault_entry SELECT * FROM vault_entry",
                              "SELECT penny_private_render_checklist('{}')"):
                with self.subTest(statement=statement),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute(statement)
