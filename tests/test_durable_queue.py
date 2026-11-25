"""Integration tests: disposable PostgreSQL only."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import psycopg

from penny.scheduler.outcomes import complete, recover_expired
from penny.scheduler.storage import TaskStore

DSN = os.environ.get("PENNY_TEST_DSN")


@unittest.skipUnless(DSN, "disposable PostgreSQL not configured")
class DurableQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Require a dedicated, empty database to prevent accidental data loss.
        with psycopg.connect(DSN, autocommit=True) as conn:
            if conn.info.dbname != "penny_test":
                raise RuntimeError("expected disposable penny_test database")
            existing = conn.execute("SELECT to_regclass('public.work_task')").fetchone()[0]
            if existing is not None:
                raise RuntimeError("database must be empty before integration suite")
            conn.execute(Path("migrations/001_scheduler.sql").read_text())

    def setUp(self):
        self.store = TaskStore(DSN)
        with psycopg.connect(DSN) as conn:
            conn.execute("TRUNCATE task_outcome,work_task,scheduler_entitlement")
            conn.execute("UPDATE scheduler_control SET paused=false,last_member_id=NULL")

    def provision(self, member, tier):
        with psycopg.connect(DSN) as conn:
            conn.execute("SELECT singleton FROM scheduler_control FOR UPDATE")
            conn.execute(
                "INSERT INTO scheduler_entitlement VALUES (%s,%s,9999999999)", (member,tier)
            )

    def test_concurrent_admission_caps(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda i: self.store.submit(uuid4(),str(i),"hello"), range(12)))
        self.assertEqual(sum(r.status == "accept" for r in results), 3)
        self.assertEqual(sum(r.status == "full" for r in results), 9)

    def test_concurrent_idempotency(self):
        member = uuid4()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.store.submit(member,"key","hello"), range(8)))
        self.assertEqual(len({r.task_id for r in results}), 1)
        self.assertEqual(sum(not r.replayed for r in results), 1)
        self.assertEqual(self.store.submit(member,"key","different").status,"idempotency_conflict")

    def test_exclusive_claim_and_restart(self):
        self.store.submit(None,"a","business")
        self.store.submit(uuid4(),"b","public")
        with ThreadPoolExecutor(max_workers=6) as pool:
            claims = list(pool.map(lambda _: TaskStore(DSN).claim(),range(6)))
        self.assertEqual(sum(c is not None for c in claims),1)
        claim = next(c for c in claims if c)
        self.assertIsNone(TaskStore(DSN).claim())
        self.assertFalse(complete(DSN,claim.task_id,uuid4(),success=True,result="wrong"))
        self.assertTrue(complete(DSN,claim.task_id,claim.fence,success=True,result="done"))
        self.assertFalse(complete(DSN,claim.task_id,claim.fence,success=True,result="again"))
        self.assertIsNotNone(TaskStore(DSN).claim())

    def test_entitlement_priority_and_recheck(self):
        low, high = uuid4(),uuid4()
        self.provision(low,1)
        self.provision(high,6)
        self.store.submit(low,"a","low")
        high_receipt = self.store.submit(high,"b","high")
        claim = self.store.claim()
        self.assertEqual(claim.task_id,high_receipt.task_id)
        self.assertTrue(complete(DSN,claim.task_id,claim.fence,success=True,result="done"))
        with psycopg.connect(DSN) as conn:
            conn.execute("SELECT singleton FROM scheduler_control FOR UPDATE")
            conn.execute("DELETE FROM scheduler_entitlement WHERE member_id=%s",(low,))
        self.assertIsNone(self.store.claim())
        with psycopg.connect(DSN) as conn:
            self.assertEqual(conn.execute(
                "SELECT status FROM task_outcome WHERE status='canceled'"
            ).fetchone()[0],"canceled")

    def test_expired_claim_requires_isolation(self):
        receipt = self.store.submit(None,"a","business")
        self.store.submit(None,"b","next")
        claim = self.store.claim()
        self.assertFalse(recover_expired(DSN,claim.task_id,claim.fence,worker_isolated=True))
        with psycopg.connect(DSN) as conn:
            conn.execute("SELECT singleton FROM scheduler_control FOR UPDATE")
            conn.execute("UPDATE work_task SET lease_until=0 WHERE id=%s",(claim.task_id,))
        self.assertIsNone(self.store.claim())
        self.assertFalse(complete(DSN,claim.task_id,claim.fence,success=True,result="late"))
        self.assertFalse(recover_expired(DSN,claim.task_id,claim.fence,worker_isolated=False))
        self.assertFalse(recover_expired(DSN,claim.task_id,uuid4(),worker_isolated=True))
        self.assertTrue(recover_expired(DSN,claim.task_id,claim.fence,worker_isolated=True))
        self.assertFalse(recover_expired(DSN,claim.task_id,claim.fence,worker_isolated=True))
        self.assertIsNotNone(self.store.claim())

    def test_pause_and_replay(self):
        member = uuid4()
        accepted = self.store.submit(member,"a","hello")
        self.store.set_paused(True)
        self.assertEqual(self.store.submit(uuid4(),"b","hello").status,"paused")
        self.assertEqual(self.store.submit(member,"a","hello").task_id,accepted.task_id)
        self.assertIsNone(self.store.claim())
        self.store.set_paused(False)
        self.assertIsNotNone(self.store.claim())


if __name__ == "__main__":
    unittest.main()
