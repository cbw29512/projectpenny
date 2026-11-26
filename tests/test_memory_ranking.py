"""Pure ranking tests and database tests of source selection and audit."""
import unittest
from uuid import uuid4

from penny.memory.ranking import search_expression, select_ranked
from penny.memory.review_state import MAX_SEARCH_TERMS


class RankingTests(unittest.TestCase):
    def test_query_operators_not_user_controlled(self):
        self.assertEqual(search_expression('SALES sales | !cost "margin"'), 
                         "sales OR cost OR margin")
        self.assertEqual(search_expression("!?"),"")
        self.assertEqual(len(search_expression(" ".join("term"+str(i) for i in range(80))).split(" OR ")),
                         MAX_SEARCH_TERMS)

    def test_duplicate_and_budget(self):
        def row(content):
            return {"source_task_id":uuid4(),"kind":"lesson","content":content}
        rows = [row("Sales outcomes"),row(" sales  OUTCOMES "),row("x"*1000),
                row("y"*700),row("Costs")]
        selected = select_ranked(rows)
        self.assertEqual([m.content for m in selected],["Sales outcomes","x"*1000,"Costs"])

    def test_invalid_input(self):
        for value in (None,"","a"*2001):
            with self.assertRaises(ValueError):
                search_expression(value)


from memory_review_fixture import DSN, ReviewFixture
from penny.memory.recall import recall
from penny.memory.task import submit_informed
import psycopg


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class RankingIntegrationTests(ReviewFixture):
    def add(self, key, content):
        source = self.candidate(key,content)
        self.assertTrue(self.approve(source,content))
        return source

    def test_relevant_older_memory_and_audit(self):
        older = self.add("old","Review shipping costs and shipping invoices")
        self.add("new","Study website typography")
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE business_memory SET approved_at=approved_at-60 WHERE source_task_id=%s",(older,))
        submit_informed(self.store,"shipping","Compare shipping invoices")
        claim = self.store.claim()
        records = recall(self.dsn,claim.task_id,claim.fence)
        self.assertEqual([m.source_task_id for m in records],[older])
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute(
                "SELECT task_id,fence,selected_count FROM memory_recall_event").fetchall(),
                [(claim.task_id,claim.fence,1)])
            self.assertEqual(conn.execute(
                "SELECT source_task_id,position FROM memory_recall_source").fetchall(),[(older,1)])

    def test_no_match_and_ordinary_task_denied(self):
        self.add("old","Shipping invoices")
        self.store.submit(None,"ordinary","Shipping invoices")
        claim = self.store.claim()
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence),())
        from penny.scheduler.outcomes import complete
        self.assertTrue(complete(self.dsn,claim.task_id,claim.fence,success=True,result="draft"))
        submit_informed(self.store,"new","Typography")
        claim = self.store.claim()
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence),())
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT selected_count FROM memory_recall_event").fetchall(),[(0,)])

    def test_audit_failure_blocks_recall(self):
        self.add("old","Measure outcomes")
        claim = self.claim()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("DROP TABLE memory_recall_source")
        with self.assertRaises(psycopg.Error):
            recall(self.dsn,claim.task_id,claim.fence)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM memory_recall_event").fetchone()[0],0)
