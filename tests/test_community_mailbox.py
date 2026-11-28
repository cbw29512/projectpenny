"""Disposable cloud suggestion admission tests; no live provider calls."""
import unittest
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import test_cloud_mailbox as mailbox
from database_fixture import DSN


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class CommunityMailboxTests(mailbox.DatabaseFixture):
    def setUp(self):
        super().setUp()
        from pathlib import Path
        import psycopg
        with psycopg.connect(self.dsn,autocommit=True) as conn:
            for path in sorted(Path("netlify/mailbox").glob("*.sql")):
                conn.execute(path.read_text())
        self.a,self.b=self.member(),self.member()

    call = mailbox.MailboxTests.call
    member = mailbox.MailboxTests.member
    enable = mailbox.MailboxTests.enable
    claim = mailbox.MailboxTests.claim
    def suggest(self,owner,key=None,body="A useful idea"):
        return self.call("SELECT * FROM community_mailbox_submit(%s,%s,%s)",
                         owner,key or uuid4(),body)[0]

    def test_community_gate_and_replay(self):
        self.enable()
        self.assertEqual(self.suggest(self.a)[0],"paused")
        self.call("UPDATE community_mailbox_control SET enabled=true RETURNING enabled")
        self.assertEqual(self.suggest(uuid4())[0],"denied")
        key=uuid4()
        first=self.suggest(self.a,key)
        self.assertEqual(first[0],"accepted")
        self.assertEqual(self.suggest(self.a,key),("accepted",first[1],True))
        self.assertEqual(self.suggest(self.a,key,"Changed idea")[0],"conflict")
        self.assertEqual(self.suggest(self.b,key)[0],"accepted")
        self.call("UPDATE mailbox_member SET enabled=false WHERE id=%s RETURNING id",self.a)
        self.assertEqual(self.suggest(self.a,key)[0],"denied")

    def test_community_concurrent_quota_and_isolation(self):
        self.call("UPDATE community_mailbox_control SET enabled=true RETURNING enabled")
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows=list(pool.map(lambda _:self.suggest(self.a),range(4)))
        self.assertEqual(sum(r[0]=="accepted" for r in rows),3)
        self.assertEqual(sum(r[0]=="member_quota" for r in rows),1)
        self.assertEqual(self.claim(),[])
        self.assertEqual(self.suggest(self.b,body="x"*501)[0],"invalid")
