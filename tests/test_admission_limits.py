"""Rolling quotas protect local inference, not the public hosting edge."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN, DatabaseFixture
from penny.auth.member_chat import MemberChatService
from penny.auth.session import issue_session
from penny.scheduler.outcomes import complete
from penny.scheduler.storage import TaskStore
from penny.scheduler.quotas import FREE_LIMITS, SUPPORTER_LIMITS


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class AdmissionLimitTests(DatabaseFixture):
    def finish(self):
        claim = self.store.claim()
        self.assertIsNotNone(claim)
        self.assertTrue(complete(self.dsn,claim.task_id,claim.fence,success=True,result="draft"))

    def test_serial_spam_after_completion_is_capped(self):
        member = uuid4()
        for i in range(FREE_LIMITS[0]):
            self.assertEqual(self.store.submit(member,str(i),"question").status,"accept")
            self.finish()
        self.assertEqual(self.store.submit(member,"new","question").status,"member_quota")
        self.assertTrue(self.store.submit(member,"0","question").replayed)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0],FREE_LIMITS[0])

    def test_sessions_do_not_reset_budget(self):
        member = uuid4()
        chat = MemberChatService(self.store)
        a,b = issue_session(self.dsn,member),issue_session(self.dsn,member)
        for i in range(FREE_LIMITS[0]):
            self.assertEqual(chat.submit(a.token,str(i),"question").status,"accept")
            self.finish()
        self.assertEqual(chat.submit(b.token,"other","question").status,"member_quota")

    def test_many_accounts_cannot_bypass_aggregate_budget(self):
        with patch("penny.scheduler.quotas.GLOBAL_LIMITS",(2,120)):
            for _ in range(2):
                self.assertEqual(self.store.submit(uuid4(),"k","question").status,"accept")
                self.finish()
            self.assertEqual(self.store.submit(uuid4(),"k","question").status,"community_quota")
            self.assertEqual(self.store.submit(None,"business","work").status,"accept")
            self.finish()

    def test_concurrent_admission_cannot_overshoot_global_budget(self):
        with patch("penny.scheduler.quotas.GLOBAL_LIMITS",(1,120)):
            with ThreadPoolExecutor(max_workers=6) as pool:
                results = list(pool.map(lambda _: TaskStore(self.dsn).submit(uuid4(),"k","question"),range(12)))
            self.assertEqual(sum(r.status=="accept" for r in results),1)
            self.assertEqual(sum(r.status=="community_quota" for r in results),11)

    def test_rolling_hour_expires_without_resetting_daily_budget(self):
        member = uuid4()
        with patch("penny.scheduler.quotas.FREE_LIMITS",(1,2)):
            self.assertEqual(self.store.submit(member,"a","question").status,"accept")
            self.finish()
            self.assertEqual(self.store.submit(member,"b","question").status,"member_quota")
            with psycopg.connect(self.dsn) as conn:
                conn.execute("UPDATE work_task SET submitted_at=submitted_at-3601 WHERE member_id=%s",(member,))
            self.assertEqual(self.store.submit(member,"b","question").status,"accept")
            self.finish()
            with psycopg.connect(self.dsn) as conn:
                conn.execute("UPDATE work_task SET submitted_at=submitted_at-3601 WHERE member_id=%s",(member,))
            self.assertEqual(self.store.submit(member,"c","question").status,"member_quota")

    def test_paid_members_still_have_caps(self):
        member = uuid4()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("INSERT INTO scheduler_entitlement VALUES (%s,6,9999999999)",(member,))
        for i in range(SUPPORTER_LIMITS[0]):
            self.assertEqual(self.store.submit(member,str(i),"question").status,"accept")
            self.finish()
        self.assertEqual(self.store.submit(member,"extra","question").status,"member_quota")

    def test_changed_identity_blocks_new_admission(self):
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertEqual(self.store.submit(uuid4(),"k","question").status,"identity_unavailable")
            self.assertEqual(self.store.submit(None,"k","work").status,"identity_unavailable")
