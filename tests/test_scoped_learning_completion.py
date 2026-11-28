"""SQL learning candidate parity and rollback, disposable PostgreSQL only."""
import json
import unittest
from uuid import uuid4

import psycopg
from psycopg import sql
from database_fixture import DSN,DatabaseFixture
from penny.memory.intake import parse_candidate,submit_review
from penny.runtime.claim_store import ScopedClaimStore
from penny.runtime.inference_db import gate_call
from penny.runtime.draft_completion import ScopedDraftCompletion


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ScopedLearningTests(DatabaseFixture):
    def reserve(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET enabled=true")
        row=gate_call(self.dsn,"begin")
        self.assertEqual(row["status"],"reserved")
        token=row["token"]
        return token,ScopedClaimStore(self.dsn,token).claim()

    def test_parser_matches_existing_python_validator(self):
        cases=[
            '{"kind":"lesson","content":"Measure first"}',
            '{"kind":"failure","content":"  Check results  "}',
            '{"kind":"skill","content":"\\u00a0Practice\\u2003"}',
            '{"kind":"lesson","kind":"idea","content":"Duplicate"}',
            '{"kind":"lesson","content":"Duplicate","content":"Again"}',
            '{"kind":"lesson","content":"Extra","approved":true}',
            '{"kind":"unknown","content":"Invalid kind"}',
            '{"kind":"lesson","content":null}',
            '{"kind":"lesson","content":"\\u0000"}',
            '{"kind":"lesson","content":"\\ud800"}',
            '{"kind":"lesson","content":"\\u00a0\\u2003"}',
            '{"kind":"lesson","content":',
            '[]','{}','null',
            json.dumps({"kind":"idea","content":"x"*1001}),
        ]
        with psycopg.connect(self.dsn) as conn:
            for raw in cases:
                with self.subTest(raw=raw[:80]):
                    expected=parse_candidate(raw)
                    rows=conn.execute("SELECT * FROM penny_private_parse_learning(%s)",(raw,)).fetchall()
                    self.assertEqual(rows,[(expected.kind.value,expected.content)] if expected else [])

    def test_invalid_candidate_keeps_outcome_without_promotion(self):
        submit_review(self.store,"invalid","Observed result")
        token,claim=self.reserve()
        result='{"kind":"lesson","content":"Unverified","approved":true}'
        self.assertTrue(ScopedDraftCompletion(token)(self.dsn,claim.task_id,claim.fence,
                         success=True,result=result))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT result FROM task_outcome").fetchall(),[(result,)])
            self.assertEqual(conn.execute("SELECT count(*) FROM memory_candidate").fetchone()[0],0)

    def test_candidate_failure_rolls_back_outcome(self):
        submit_review(self.store,"rollback","Observed result")
        token,claim=self.reserve()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("""CREATE FUNCTION reject_learning() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic failure'; END; $$""")
            conn.execute("""CREATE TRIGGER reject_learning BEFORE INSERT ON memory_candidate
                FOR EACH ROW EXECUTE FUNCTION reject_learning()""")
        with self.assertRaises(psycopg.Error):
            ScopedDraftCompletion(token)(self.dsn,claim.task_id,claim.fence,
                success=True,result='{"kind":"lesson","content":"Measure"}')
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM task_outcome").fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT state FROM work_task").fetchone()[0],"running")

    def test_restricted_role_can_stage_but_not_approve(self):
        submit_review(self.store,"restricted","Observed result")
        token,claim=self.reserve()
        role=sql.Identifier("learning_"+uuid4().hex)
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
                (token,claim.task_id,claim.fence,'{"kind":"lesson","content":"Measure"}')).fetchone()[0],"completed")
            for statement in ("SELECT * FROM memory_candidate",
                              "SELECT * FROM penny_private_parse_learning('{}')",
                              "INSERT INTO business_memory SELECT * FROM business_memory",
                              "UPDATE memory_candidate SET content='Forged'"):
                with self.subTest(statement=statement),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute(statement)
