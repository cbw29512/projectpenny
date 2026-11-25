"""Review lifecycle integration tests in a disposable isolated schema."""
import os
import unittest
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from penny.memory.intake import submit_review
from penny.memory.recall import recall
from penny.memory.review import approve, revoke
from penny.scheduler.outcomes import complete
from penny.scheduler.storage import TaskStore

DSN = os.environ.get("PENNY_TEST_DSN")
CONTENT = "Measure outcomes first."


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.schema = "review_test_" + uuid4().hex
        with psycopg.connect(DSN, autocommit=True) as conn:
            if conn.info.dbname != "penny_test":
                raise RuntimeError("expected disposable penny_test database")
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.addCleanup(self.drop_schema)
        self.dsn = make_conninfo(DSN, options="-c search_path=" + self.schema)
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            for path in sorted(Path("migrations").glob("*.sql")):
                conn.execute(path.read_text())
        self.store = TaskStore(self.dsn)
        self.reviewer = uuid4()

    def drop_schema(self):
        with psycopg.connect(DSN, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))

    def candidate(self, key="a", content=CONTENT):
        import json
        receipt = submit_review(self.store,key,"Observed result")
        claim = self.store.claim()
        self.assertTrue(complete(self.dsn,claim.task_id,claim.fence,success=True,
                                 result=json.dumps({"kind":"lesson","content":content})))
        return receipt.task_id

    def approve(self, source, content=CONTENT, **kwargs):
        args = dict(reviewer_id=self.reviewer,review_ref="review/1",
                    evidence=b"independently reviewed material",expected_content=content,
                    retention_seconds=3600)
        args.update(kwargs)
        return approve(self.dsn,source,**args)

    def claim(self, member=None):
        self.store.submit(member,str(uuid4()),"draft")
        return self.store.claim()

    def test_quarantine_approval_and_revocation(self):
        source = self.candidate()
        claim = self.claim()
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence), ())
        self.assertTrue(self.approve(source))
        self.assertFalse(self.approve(source))
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence)[0].content,CONTENT)
        self.assertTrue(revoke(self.dsn,source,reviewer_id=self.reviewer,review_ref="review/2"))
        self.assertFalse(revoke(self.dsn,source,reviewer_id=self.reviewer,review_ref="review/2"))
        self.assertFalse(self.approve(source))
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence), ())
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory_event").fetchone()[0],2)

    def test_missing_candidate_and_mismatched_snapshot(self):
        self.assertFalse(self.approve(uuid4()))
        self.assertFalse(self.approve(self.candidate(), "changed"))
        with self.assertRaises(ValueError):
            self.approve(uuid4(), evidence=b"")
        with self.assertRaises(ValueError):
            self.approve(uuid4(), reviewer_id="forged")
        with self.assertRaises(ValueError):
            self.approve(uuid4(), retention_seconds=True)

    def test_public_claim_cannot_recall(self):
        self.assertTrue(self.approve(self.candidate()))
        claim = self.claim(uuid4())
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence), ())

    def test_stale_fence_pause_and_expired_memory(self):
        source = self.candidate()
        self.assertTrue(self.approve(source))
        claim = self.claim()
        self.assertEqual(recall(self.dsn,claim.task_id,uuid4()), ())
        self.store.set_paused(True)
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence), ())
        self.store.set_paused(False)
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE business_memory SET approved_at=1,expires_at=2")
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence), ())

    def test_bounded_complete_records(self):
        for i in range(4):
            content = str(i) + "x" * 799
            self.assertTrue(self.approve(self.candidate(str(i),content),content))
        claim = self.claim()
        records = recall(self.dsn,claim.task_id,claim.fence)
        self.assertEqual(len(records),1)
        self.assertEqual(len(records[0].content),800)

    def test_approval_atomic_with_audit(self):
        source = self.candidate()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("DROP TABLE business_memory_event")
        with self.assertRaises(psycopg.Error):
            self.approve(source)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM business_memory").fetchone()[0],0)
