"""Isolated PostgreSQL mailbox tests. Never connect to live Netlify."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import psycopg
from database_fixture import DSN, DatabaseFixture


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class MailboxTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        # Separate schema from the local scheduler to verify independence.
        # The disposable fixture owns this schema; no cloud calls occur.
        with psycopg.connect(self.dsn,autocommit=True) as conn:
            for path in sorted(Path("netlify/mailbox").glob("*.sql")):
                conn.execute(path.read_text())
        self.a,self.b = self.member(),self.member()

    def call(self,query,*args):
        with psycopg.connect(self.dsn) as conn:
            return conn.execute(query,args).fetchall()

    def member(self):
        member=uuid4()
        self.call("INSERT INTO mailbox_member(id) VALUES (%s) RETURNING id",member)
        return member

    def enable(self):
        self.call("UPDATE mailbox_control SET enabled=true RETURNING enabled")

    def submit(self,owner,key=None,text="Hi"):
        return self.call("SELECT * FROM mailbox_submit(%s,%s,%s)",owner,key or uuid4(),text)[0]

    def claim(self):
        return self.call("SELECT * FROM mailbox_claim()")

    def deliver(self,question,answer="Penny reply"):
        row=self.claim()[0]
        self.assertEqual(row[0],question)
        self.assertTrue(self.call("SELECT mailbox_ack(%s,%s,%s)",question,row[3],uuid4())[0][0])
        self.assertTrue(self.call("SELECT mailbox_answer(%s,%s,%s)",question,row[3],answer)[0][0])
        return row[3]

    def test_default_closed_and_allowlisted_only(self):
        self.assertEqual(self.submit(self.a)[0],"paused")
        self.enable()
        self.assertEqual(self.submit(uuid4())[0],"denied")
        self.assertEqual(self.submit(self.a,text="   ")[0],"invalid")
        self.assertEqual(self.submit(self.a,text="x"*2001)[0],"invalid")
        self.assertEqual(self.submit(self.a)[0],"accepted")

    def test_idempotency_and_owner_scope(self):
        self.enable()
        key=uuid4()
        first=self.submit(self.a,key)
        self.assertEqual(self.submit(self.a,key),("accepted",first[1],True))
        self.assertEqual(self.submit(self.a,key,"different")[0],"conflict")
        self.assertEqual(self.submit(self.a)[0],"member_busy")
        self.assertEqual(self.call("SELECT * FROM mailbox_read(%s,%s)",self.b,first[1]),[])
        self.deliver(first[1])
        self.assertEqual(self.call("SELECT * FROM mailbox_read(%s,%s)",self.a,first[1]),
                         [(first[1],"answered","Penny reply")])

    def test_fence_ack_and_duplicate_answer(self):
        self.enable()
        q=self.submit(self.a)[1]
        row=self.claim()[0]
        fence=row[3]
        self.assertEqual(self.claim(),[])
        self.assertFalse(self.call("SELECT mailbox_answer(%s,%s,%s)",q,fence,"early")[0][0])
        self.assertFalse(self.call("SELECT mailbox_ack(%s,%s,%s)",q,uuid4(),uuid4())[0][0])
        local=uuid4()
        for _ in range(2):
            self.assertTrue(self.call("SELECT mailbox_ack(%s,%s,%s)",q,fence,local)[0][0])
        self.assertFalse(self.call("SELECT mailbox_ack(%s,%s,%s)",q,fence,uuid4())[0][0])
        for _ in range(2):
            self.assertTrue(self.call("SELECT mailbox_answer(%s,%s,%s)",q,fence,"reply")[0][0])
        self.assertFalse(self.call("SELECT mailbox_answer(%s,%s,%s)",q,fence,"changed")[0][0])

    def test_expired_claim_never_reissued(self):
        self.enable()
        q=self.submit(self.a)[1]
        fence=self.claim()[0][3]
        self.call("UPDATE mailbox_question SET lease_until=clock_timestamp()-interval '1 second' WHERE id=%s RETURNING id",q)
        self.assertEqual(self.claim(),[])
        self.assertFalse(self.call("SELECT mailbox_ack(%s,%s,%s)",q,fence,uuid4())[0][0])
        self.assertEqual(self.call("SELECT * FROM mailbox_read(%s,%s)",self.a,q),[(q,"expired",None)])

    def test_spam_after_completion_and_concurrent_cap(self):
        self.enable()
        for _ in range(3):
            self.deliver(self.submit(self.a)[1])
        self.assertEqual(self.submit(self.a)[0],"member_quota")
        members=[self.member() for _ in range(12)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(self.submit,members))
        self.assertEqual(sum(r[0]=="accepted" for r in results),8)
        self.assertEqual(sum(r[0]=="full" for r in results),4)

    def test_cross_account_hourly_budget(self):
        self.enable()
        for _ in range(20):
            self.deliver(self.submit(self.member())[1])
        self.assertEqual(self.submit(self.b)[0],"community_quota")

    def test_disabled_member_cannot_read_or_receive(self):
        self.enable()
        q=self.submit(self.a)[1]
        fence=self.claim()[0][3]
        self.call("UPDATE mailbox_member SET enabled=false WHERE id=%s RETURNING id",self.a)
        self.assertFalse(self.call("SELECT mailbox_ack(%s,%s,%s)",q,fence,uuid4())[0][0])
        self.assertEqual(self.call("SELECT * FROM mailbox_read(%s,%s)",self.a,q),[])

    def test_reject_and_retention(self):
        self.enable()
        q=self.submit(self.a)[1]
        fence=self.claim()[0][3]
        self.assertTrue(self.call("SELECT mailbox_reject(%s,%s)",q,fence)[0][0])
        self.assertTrue(self.call("SELECT mailbox_reject(%s,%s)",q,fence)[0][0])
        self.assertEqual(self.call("SELECT mailbox_purge()"),[(0,)])
        self.call("UPDATE mailbox_question SET submitted_at=clock_timestamp()-interval '49 hours' WHERE id=%s RETURNING id",q)
        self.assertEqual(self.call("SELECT mailbox_purge()"),[(1,)])
