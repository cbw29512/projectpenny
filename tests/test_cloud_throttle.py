"""Real shared SQL counters; no live service or credentials."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
from database_fixture import DSN
from cloud_role_fixture import CloudRoleFixture


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class CloudThrottleTests(CloudRoleFixture):
    def member_attempt(self,op="submit",owner=None):
        return self.call("member","SELECT mailbox_allow_member(%s,%s)",owner or self.a,op)[0][0]

    def bridge_attempt(self,op="claim"):
        return self.call("bridge","SELECT mailbox_allow_bridge(%s)",op)[0][0]

    def stabilize(self):
        # Deterministic fixture: a future minute bucket prevents a test run
        # crossing a minute boundary from resetting its counters.
        self.call("owner","UPDATE mailbox_attempt_global SET minute_bucket=999999999,day_bucket=9999999 RETURNING op")

    def test_serial_and_parallel_attempts_share_quota(self):
        self.stabilize()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:self.member_attempt(),range(16)))
        self.assertEqual(sum(results),6)
        self.assertFalse(self.member_attempt())
        self.assertTrue(self.member_attempt(owner=self.b))

    def test_read_budget_is_independent(self):
        self.stabilize()
        self.assertEqual(sum(self.member_attempt("read") for _ in range(14)),12)
        self.assertTrue(self.member_attempt("submit"))

    def test_global_quota_applies_across_members(self):
        self.stabilize()
        self.call("owner","UPDATE mailbox_attempt_global SET minute_count=39 WHERE op='submit' RETURNING op")
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda owner:self.member_attempt(owner=owner),[self.a,self.b]*4))
        self.assertEqual(sum(results),1)

    def test_daily_budget_prevents_minute_reset_bypass(self):
        self.stabilize()
        self.call("owner","UPDATE mailbox_attempt_global SET day_count=600 WHERE op='submit' RETURNING op")
        self.assertFalse(self.member_attempt())
        self.assertTrue(self.member_attempt("read"))

    def test_window_reset_reuses_rows(self):
        self.stabilize()
        for _ in range(6):
            self.assertTrue(self.member_attempt())
        self.call("owner","UPDATE mailbox_attempt_global SET minute_bucket=0 WHERE op='submit' RETURNING op")
        self.call("owner","UPDATE mailbox_attempt_member SET minute_bucket=0 RETURNING owner_id")
        self.assertTrue(self.member_attempt())
        self.assertEqual(self.call("owner","SELECT count(*) FROM mailbox_attempt_member"),[(1,)])

    def test_unknown_and_disabled_member_cannot_allocate_buckets(self):
        self.assertFalse(self.member_attempt(owner=uuid4()))
        self.call("owner","UPDATE mailbox_member SET enabled=false WHERE id=%s RETURNING id",self.a)
        self.assertFalse(self.member_attempt())
        self.assertEqual(self.call("owner","SELECT count(*) FROM mailbox_attempt_member"),[(0,)])

    def test_bridge_own_budget_and_fixed_operations(self):
        self.stabilize()
        self.assertEqual(sum(self.bridge_attempt() for _ in range(8)),6)
        self.assertTrue(self.bridge_attempt("answer"))
        self.assertFalse(self.bridge_attempt("submit"))
        self.assertFalse(self.member_attempt("claim"))

    def test_roles_cannot_bypass_or_mutate_counters(self):
        for role,query,args in [
            ("member","SELECT mailbox_allow_bridge('claim')",()),
            ("bridge","SELECT mailbox_allow_member(%s,'submit')",(self.a,)),
            ("member","SELECT mailbox_take_attempt('submit',%s)",(self.a,)),
            ("bridge","SELECT * FROM mailbox_attempt_global",()),
            ("member","UPDATE mailbox_attempt_global SET minute_count=0 RETURNING op",()),
            ("maintenance","SELECT mailbox_allow_bridge('claim')",()),
        ]:
            with self.subTest(role=role,query=query):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    self.call(role,query,*args)
