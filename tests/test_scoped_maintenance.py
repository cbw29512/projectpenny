"""Scoped maintenance parser and restricted atomic intake regression."""
import json
import unittest
from uuid import uuid4

import psycopg
from psycopg import sql
from memory_review_fixture import DSN,ReviewFixture
from penny.memory.maintenance import submit_maintenance
from penny.memory.maintenance_parse import parse_maintenance
from penny.memory.review import revoke
from penny.runtime.business_recall import ScopedBusinessRecall
from penny.runtime.claim_store import ScopedClaimStore
from penny.runtime.inference_db import gate_call
from penny.runtime.draft_completion import ScopedDraftCompletion


def raw(action,sources,replacement=None):
    return json.dumps(dict(action=action,sources=[str(s) for s in sources],
                           rationale="  Review shipping outcomes  ",replacement=replacement))


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ScopedMaintenanceTests(ReviewFixture):
    def test_parser_parity(self):
        a,b=uuid4(),uuid4()
        for value in (raw("correct",[a]," revised "),raw("outdated",[a]),
                      raw("consolidate",[a,b],"merge"),raw("contradiction",[a,b]),
                      raw("correct",[a]),raw("consolidate",[a,a],"merge"),
                      raw("outdated",[a],"invalid"),raw("outdated",[str(a).upper()]),
                      raw("outdated",[a]).replace('"action":','"action":"correct","action":'),
                      raw("correct",[a],"\x00"),"{}","[]","not json"):
            with self.subTest(value=value),psycopg.connect(self.dsn) as conn:
                expected=parse_maintenance(value)
                actual=conn.execute("SELECT * FROM penny_private_parse_maintenance(%s)",(value,)).fetchall()
                self.assertEqual(actual,[] if expected is None else [
                    (expected.action.value,list(expected.sources),expected.rationale,expected.replacement)])

    def start(self):
        a=self.candidate("a","Shipping costs")
        self.assertTrue(self.approve(a,"Shipping costs"))
        b=self.candidate("b","Typography")
        self.assertTrue(self.approve(b,"Typography"))
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET enabled=true")
        submit_maintenance(self.store,"review","Shipping")
        token=gate_call(self.dsn,"begin")["token"]
        claim=ScopedClaimStore(self.dsn,token).claim()
        self.assertEqual([r.source_task_id for r in ScopedBusinessRecall(token)(
            self.dsn,claim.task_id,claim.fence)],[a])
        return a,b,token,claim

    def test_restricted_completion(self):
        a,b,token,claim=self.start()
        role=sql.Identifier("maintenance_"+uuid4().hex)
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
                (token,claim.task_id,claim.fence,raw("outdated",[a]))).fetchone()[0],"completed")
            for statement in ("UPDATE business_memory SET revoked_at=approved_at",
                              "SELECT * FROM memory_maintenance_proposal",
                              "SELECT * FROM penny_private_parse_maintenance('{}')",
                              "SELECT penny_private_stage_maintenance(NULL,NULL,NULL,NULL)"):
                with self.subTest(statement=statement),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute(statement)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT action,state FROM memory_maintenance_proposal").fetchall(),
                             [("outdated","quarantined")])
            self.assertEqual(conn.execute("SELECT source_task_id FROM memory_maintenance_source").fetchall(),[(a,)])
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory WHERE revoked_at IS NULL").fetchone()[0],2)

    def test_unrecalled_source_never_staged(self):
        a,b,token,claim=self.start()
        self.assertTrue(ScopedDraftCompletion(token)(self.dsn,claim.task_id,claim.fence,
                        success=True,result=raw("consolidate",[a,b],"merged")))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM memory_maintenance_proposal").fetchone()[0],0)

    def test_revoked_source_never_staged(self):
        a,b,token,claim=self.start()
        self.assertTrue(revoke(self.dsn,a,reviewer_id=self.reviewer,review_ref="review/2"))
        self.assertTrue(ScopedDraftCompletion(token)(self.dsn,claim.task_id,claim.fence,
                        success=True,result=raw("outdated",[a])))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM memory_maintenance_proposal").fetchone()[0],0)

    def test_atomic_rollback(self):
        a,b,token,claim=self.start()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("DROP TABLE memory_maintenance_source")
        with self.assertRaises(psycopg.Error):
            ScopedDraftCompletion(token)(self.dsn,claim.task_id,claim.fence,
                        success=True,result=raw("outdated",[a]))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT state FROM work_task WHERE id=%s",(claim.task_id,)).fetchone()[0],"running")
            self.assertEqual(conn.execute("SELECT count(*) FROM memory_maintenance_proposal").fetchone()[0],0)
