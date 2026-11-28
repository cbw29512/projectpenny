"""Shared Workshop attempt budgets on disposable PostgreSQL."""
import unittest
from concurrent.futures import ThreadPoolExecutor
import psycopg
from database_fixture import DSN
from cloud_role_fixture import CloudRoleFixture


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class WorkshopThrottleTests(CloudRoleFixture):
    def read(self):
        return self.call("projection_reader","SELECT workshop_allow_read()")[0][0]

    def write(self):
        return self.call("projection_writer","SELECT workshop_allow_write()")[0][0]

    def enable(self):
        self.call("owner","UPDATE workshop_observation SET enabled=true RETURNING singleton")
        self.call("owner","UPDATE workshop_attempt_budget SET minute_bucket=999999999,day_bucket=9999999 RETURNING op")

    def test_closed_then_parallel_write_budget(self):
        self.assertFalse(self.write())
        self.assertFalse(self.read())
        self.enable()
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(lambda _:self.write(),range(12)))
        self.assertEqual(sum(results),2)
        self.assertFalse(self.write())
        self.assertTrue(self.read())

    def test_daily_limit_and_independent_read_budget(self):
        self.enable()
        self.call("owner","UPDATE workshop_attempt_budget SET day_count=1799 WHERE op='read' RETURNING op")
        self.assertTrue(self.read())
        self.assertFalse(self.read())
        self.assertTrue(self.write())
        self.call("owner","UPDATE workshop_attempt_budget SET minute_bucket=0 WHERE op='read' RETURNING op")
        self.assertFalse(self.read())

    def test_no_cross_scope_or_raw_counter_access(self):
        for role,query in (
            ("projection_writer","SELECT workshop_allow_read()"),
            ("projection_reader","SELECT workshop_allow_write()"),
            ("projection_reader","SELECT workshop_take_attempt('read')"),
            ("member","SELECT workshop_allow_read()"),
            ("bridge","SELECT workshop_allow_write()"),
            ("projection_writer","SELECT * FROM workshop_attempt_budget"),
            ("projection_reader","UPDATE workshop_attempt_budget SET day_count=0 RETURNING op"),
        ):
            with self.subTest(role=role,query=query):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    self.call(role,query)
