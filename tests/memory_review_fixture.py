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


class ReviewFixture(unittest.TestCase):
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
        from penny.memory.task import submit_informed
        if member is None:
            submit_informed(self.store,uuid4().hex,"Measure outcomes")
        else:
            self.store.submit(member,str(uuid4()),"Measure outcomes")
        return self.store.claim()

