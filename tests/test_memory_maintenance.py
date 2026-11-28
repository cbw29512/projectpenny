"""Parser and PostgreSQL maintenance proposal safety tests."""
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from memory_review_fixture import DSN, ReviewFixture
from penny.guardian.state import Decision
from penny.memory.maintenance import submit_maintenance
from penny.memory.maintenance_parse import parse_maintenance
from penny.memory.recall import recall
from penny.memory.review import revoke
from penny.scheduler.outcomes import complete


def proposal(action, sources, replacement=None):
    return json.dumps({"action":action,"sources":[str(s) for s in sources],
                       "rationale":"Review observed outcomes","replacement":replacement})


class MaintenanceParserTests(unittest.TestCase):
    def test_valid_actions(self):
        a,b = uuid4(),uuid4()
        for raw in (proposal("correct",[a],"new"),proposal("outdated",[a]),
                    proposal("consolidate",[a,b],"merged"),proposal("contradiction",[a,b])):
            self.assertIsNotNone(parse_maintenance(raw))

    def test_invalid_shapes_and_cardinality(self):
        a,b = uuid4(),uuid4()
        for raw in (None,"{}",proposal("revoke",[a]),proposal("correct",[a]),
                    proposal("outdated",[a],"replace"),proposal("consolidate",[a,a],"merge"),
                    proposal("contradiction",[a]),proposal("correct",[a,b],"replace"),
                    proposal("correct",[a],"x"*1001),proposal("outdated",["bad"]),
                    proposal("outdated",[a]).replace('"action":','"approved":true,"action":')):
            self.assertIsNone(parse_maintenance(raw))


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class MaintenanceTests(ReviewFixture):
    def approved(self, key="a", content="Measure shipping outcomes"):
        source = self.candidate(key,content)
        self.assertTrue(self.approve(source,content))
        return source

    def start(self):
        submit_maintenance(self.store,"review","shipping outcomes")
        claim = self.store.claim()
        self.assertTrue(claim.memory_enabled)
        return claim

    def finish(self, claim, raw, fence=None):
        return complete(self.dsn,claim.task_id,fence or claim.fence,success=True,result=raw)

    def count(self):
        with psycopg.connect(self.dsn) as conn:
            return conn.execute("SELECT count(*) FROM memory_maintenance_proposal").fetchone()[0]

    def test_recalled_sources_quarantined_without_mutating_memory(self):
        a = self.approved()
        b = self.approved("b","Review shipping invoices")
        claim = self.start()
        self.assertEqual({x.source_task_id for x in recall(self.dsn,claim.task_id,claim.fence)},{a,b})
        raw = proposal("consolidate",[a,b],"Measure shipping costs and outcomes")
        self.assertFalse(self.finish(claim,raw,uuid4()))
        self.assertTrue(self.finish(claim,raw))
        self.assertFalse(self.finish(claim,raw))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT state,action FROM memory_maintenance_proposal").fetchall(),
                             [("quarantined","consolidate")])
            self.assertEqual(conn.execute("SELECT count(*) FROM memory_maintenance_source").fetchone()[0],2)
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory WHERE revoked_at IS NULL").fetchone()[0],2)

    def test_unrecalled_or_forged_source_rejected(self):
        a = self.approved()
        b = self.approved("b","Typography")
        claim = self.start()
        self.assertEqual([x.source_task_id for x in recall(self.dsn,claim.task_id,claim.fence)],[a])
        self.assertTrue(self.finish(claim,proposal("consolidate",[a,b],"merged")))
        self.assertEqual(self.count(),0)

    def test_revocation_after_recall_rejects_proposal(self):
        a = self.approved()
        claim = self.start()
        recall(self.dsn,claim.task_id,claim.fence)
        self.assertTrue(revoke(self.dsn,a,reviewer_id=self.reviewer,review_ref="review/2"))
        self.assertTrue(self.finish(claim,proposal("outdated",[a])))
        self.assertEqual(self.count(),0)

    def test_guardian_denial_and_member_forgery(self):
        from penny.memory.maintenance_state import MAINTENANCE_PREFIX
        a = self.approved()
        claim = self.start()
        recall(self.dsn,claim.task_id,claim.fence)
        with patch("penny.memory.maintenance.authorize",return_value=Decision(False,"denied")):
            self.assertTrue(self.finish(claim,proposal("outdated",[a])))
        self.store.submit(uuid4(),MAINTENANCE_PREFIX+"forged","shipping")
        claim = self.store.claim()
        self.assertTrue(self.finish(claim,proposal("outdated",[a])))
        self.assertEqual(self.count(),0)

    def test_instruction_words_are_not_recall_terms(self):
        relevant = self.approved()
        self.approved("noise","Historical review of correction and consolidation proposals")
        claim = self.start()
        self.assertEqual([m.source_task_id for m in recall(self.dsn,claim.task_id,claim.fence)],
                         [relevant])

    def test_storage_failure_rolls_back_outcome(self):
        a = self.approved()
        claim = self.start()
        recall(self.dsn,claim.task_id,claim.fence)
        with psycopg.connect(self.dsn) as conn:
            conn.execute("DROP TABLE memory_maintenance_source")
        with self.assertRaises(psycopg.Error):
            self.finish(claim,proposal("outdated",[a]))
        self.assertEqual(self.count(),0)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT state FROM work_task WHERE id=%s",
                                         (claim.task_id,)).fetchone()[0],"running")
