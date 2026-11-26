"""Dedicated shared admin budgets; disposable database only."""
from concurrent.futures import ThreadPoolExecutor
import unittest
from uuid import uuid4

import psycopg
from database_fixture import DSN
from cloud_role_fixture import CloudRoleFixture


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class AdminThrottleTests(CloudRoleFixture):
    def setUp(self):
        super().setUp()
        self.admin=uuid4()
        self.call("owner","INSERT INTO mailbox_admin(id) VALUES (%s) RETURNING id",self.admin)
        # Freeze bucket rollover for deterministic concurrency tests.
        self.call("owner","UPDATE mailbox_admin_budget SET minute_bucket=999999999,day_bucket=9999999 RETURNING op")

    def allow(self,op="status",subject=None):
        return self.call("admin","SELECT mailbox_admin_allow(%s,%s)",subject or self.admin,op)[0][0]

    def test_parallel_status_budget_and_independent_pause(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(lambda _:self.allow(),range(18)))
        self.assertEqual(sum(results),12)
        self.assertFalse(self.allow())
        self.assertTrue(self.allow("pause"))

    def test_pause_budget_and_daily_limit(self):
        self.assertEqual(sum(self.allow("pause") for _ in range(8)),6)
        self.call("owner","UPDATE mailbox_admin_budget SET day_count=360 WHERE op='status' RETURNING op")
        self.assertFalse(self.allow())

    def test_unprovisioned_disabled_and_unknown_operation(self):
        self.assertFalse(self.allow(subject=self.a))
        self.assertFalse(self.allow("resume"))
        self.call("owner","UPDATE mailbox_admin SET enabled=false WHERE id=%s RETURNING id",self.admin)
        self.assertFalse(self.allow())
        self.assertEqual(self.call("owner","SELECT sum(minute_count) FROM mailbox_admin_budget"),[(0,)])

    def test_runtime_roles_cannot_mutate_or_share_admin_budget(self):
        for role in ("member","bridge","maintenance"):
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                self.call(role,"SELECT mailbox_admin_allow(%s,'status')",self.admin)
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.call("admin","UPDATE mailbox_admin_budget SET minute_count=0 RETURNING op")
        self.assertTrue(self.allow())
