"""Scoped business recall tests on a disposable PostgreSQL database."""
import unittest
from unittest.mock import Mock
from uuid import uuid4

import psycopg
from psycopg import sql
from memory_review_fixture import DSN,ReviewFixture
from penny.memory.task import submit_informed
from penny.memory.maintenance import submit_maintenance
from penny.runtime.business_recall import ScopedBusinessRecall
from penny.runtime.claim_store import ScopedClaimStore
from penny.runtime.inference_db import gate_call
from penny.runtime.inference import inference_tick


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ScopedBusinessTests(ReviewFixture):
    def setUp(self):
        super().setUp()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET enabled=true")

    def add(self,key,content):
        source=self.candidate(key,content)
        self.assertTrue(self.approve(source,content))
        return source

    def reserved_claim(self):
        reservation=gate_call(self.dsn,"begin")
        self.assertEqual(reservation["status"],"reserved")
        token=reservation["token"]
        return token,ScopedClaimStore(self.dsn,token).claim()

    def test_reviewed_relevant_records_and_audit(self):
        source=self.add("shipping","Shipping invoices and costs")
        self.add("typography","Website typography")
        self.candidate("unreviewed","Shipping unreviewed claim")
        submit_informed(self.store,"lookup","Shipping invoices")
        brain=Mock()
        brain.generate_with_memory.return_value="Draft"
        self.assertEqual(inference_tick(self.dsn,brain),"completed")
        records=brain.generate_with_memory.call_args.args[2]
        self.assertEqual([r.source_task_id for r in records],[source])
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT source_task_id FROM memory_recall_source").fetchall(),[(source,)])

    def test_maintenance_search_uses_only_topic(self):
        source=self.add("topic","Shipping costs")
        self.add("instructions","Review historical memories and rationale")
        submit_maintenance(self.store,"topic","Shipping")
        token,claim=self.reserved_claim()
        reader=ScopedBusinessRecall(token)
        self.assertEqual(reader(self.dsn,claim.task_id,uuid4()),())
        self.assertEqual([r.source_task_id for r in reader(self.dsn,claim.task_id,claim.fence)],[source])
        with self.assertRaises(psycopg.Error):
            reader(self.dsn,claim.task_id,claim.fence)

    def test_empty_recall_is_audited_and_consumed(self):
        submit_informed(self.store,"empty","Shipping")
        token,claim=self.reserved_claim()
        reader=ScopedBusinessRecall(token)
        self.assertEqual(reader(self.dsn,claim.task_id,claim.fence),())
        with self.assertRaises(psycopg.Error):
            reader(self.dsn,claim.task_id,claim.fence)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT selected_count FROM memory_recall_event").fetchall(),[(0,)])

    def test_restricted_role_and_revoked_memory(self):
        source=self.add("allowed","Shipping costs")
        revoked=self.add("revoked","Shipping rates")
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE business_memory SET revoked_at=approved_at WHERE source_task_id=%s",(revoked,))
        submit_informed(self.store,"allowed","Shipping")
        token,claim=self.reserved_claim()
        role=sql.Identifier("business_"+uuid4().hex)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(role))
            conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(self.schema),role))
            conn.execute(sql.SQL("GRANT EXECUTE ON FUNCTION penny_inference_business_recall(uuid,uuid,uuid) TO {}").format(role))

        def cleanup():
            with psycopg.connect(self.dsn) as conn:
                conn.execute(sql.SQL("DROP OWNED BY {}").format(role))
                conn.execute(sql.SQL("DROP ROLE {}").format(role))
        self.addCleanup(cleanup)
        with psycopg.connect(self.dsn) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(role))
            rows=conn.execute("SELECT * FROM penny_inference_business_recall(%s,%s,%s)",
                              (token,claim.task_id,claim.fence)).fetchall()
            self.assertEqual([r[0] for r in rows],[source])
            for statement in ("SELECT * FROM business_memory","SELECT * FROM member_memory",
                              "UPDATE business_memory SET revoked_at=NULL",
                              "DELETE FROM memory_recall_event",
                              "INSERT INTO business_memory SELECT * FROM business_memory"):
                with self.subTest(statement=statement),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute(statement)
