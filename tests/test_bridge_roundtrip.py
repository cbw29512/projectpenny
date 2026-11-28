"""Two isolated PostgreSQL schemas, real queue/bridge SQL, synthetic inference."""
from datetime import timezone
from pathlib import Path
import unittest
from unittest.mock import Mock
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from database_fixture import DSN, DatabaseFixture
from penny.bridge.state import BridgeResult, RemoteClaim
from penny.bridge.worker import run_bridge_once
from penny.bridge.release import approve_reply
from penny.scheduler.worker import run_once, WorkerResult


class CloudSQLClient:
    """Test-only adapter bypasses HTTP, not cloud SQL state transitions."""
    def __init__(self, dsn):
        self.dsn=dsn

    def query(self, statement, *args):
        with psycopg.connect(self.dsn) as conn:
            return conn.execute(statement,args).fetchone()

    def claim(self):
        row=self.query("SELECT * FROM mailbox_claim()")
        if row is None:
            return BridgeResult("empty")
        q,owner,body,fence,lease=row
        return BridgeResult("claimed",RemoteClaim(q,owner,fence,lease.astimezone(timezone.utc),body))

    def ack(self,q,fence,task):
        ok=self.query("SELECT mailbox_ack(%s,%s,%s)",q,fence,task)[0]
        return BridgeResult("ok" if ok else "conflict")

    def answer(self,q,fence,text):
        ok=self.query("SELECT mailbox_answer(%s,%s,%s)",q,fence,text)[0]
        return BridgeResult("ok" if ok else "conflict")

    def reject(self,q,fence):
        ok=self.query("SELECT mailbox_reject(%s,%s)",q,fence)[0]
        return BridgeResult("ok" if ok else "conflict")


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class BridgeRoundtripTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.cloud_schema=self.schema+"_cloud"
        with psycopg.connect(DSN,autocommit=True) as conn:
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.cloud_schema)))
        self.addCleanup(self.drop_cloud)
        cloud_dsn=make_conninfo(DSN,options="-c search_path="+self.cloud_schema)
        with psycopg.connect(cloud_dsn,autocommit=True) as conn:
            for path in sorted(Path("netlify/mailbox").glob("*.sql")):
                conn.execute(path.read_text())
        self.cloud=CloudSQLClient(cloud_dsn)
        self.owner,self.other,self.member=uuid4(),uuid4(),uuid4()
        with psycopg.connect(cloud_dsn) as conn:
            conn.execute("UPDATE mailbox_control SET enabled=true")
            conn.execute("INSERT INTO mailbox_member(id) VALUES (%s),(%s)",(self.owner,self.other))
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE bridge_control SET enabled=true")
            conn.execute("INSERT INTO bridge_member VALUES (%s,%s,true)",(self.owner,self.member))

    def drop_cloud(self):
        with psycopg.connect(DSN,autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.cloud_schema)))

    def tick(self):
        # Synthetic advance of the operator-controlled cooldown only.
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE bridge_control SET not_before=0")
        return run_bridge_once(self.dsn,self.cloud).status

    def test_private_conversation_roundtrip(self):
        key=uuid4()
        question="What is your mission?"
        receipt=self.cloud.query("SELECT * FROM mailbox_submit(%s,%s,%s)",self.owner,key,question)
        self.assertEqual(receipt[0],"accepted")
        q=receipt[1]
        self.assertEqual(self.cloud.query("SELECT * FROM mailbox_submit(%s,%s,%s)",self.owner,key,question),
                         ("accepted",q,True))
        self.assertEqual(self.tick(),"admitted")
        self.assertEqual(self.tick(),"acknowledged")
        self.assertEqual(self.cloud.query("SELECT * FROM mailbox_read(%s,%s)",self.owner,q),
                         (q,"locally_accepted",None))
        brain=Mock()
        draft="Penny here. My mission is legitimate commercial earnings."
        brain.generate.return_value=draft
        self.assertEqual(run_once(self.store,brain),WorkerResult.COMPLETED)
        self.assertEqual(brain.generate.call_args.args[0],question)
        self.assertEqual(self.tick(),"waiting_review")
        self.assertTrue(approve_reply(self.dsn,q,reviewer_id=uuid4(),expected_text=draft))
        self.assertEqual(self.tick(),"delivered")
        self.assertEqual(self.cloud.query("SELECT * FROM mailbox_read(%s,%s)",self.owner,q),
                         (q,"answered",draft))
        self.assertIsNone(self.cloud.query("SELECT * FROM mailbox_read(%s,%s)",self.other,q))
        self.assertEqual(self.tick(),"empty")
        brain.generate.assert_called_once()
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0],1)
            self.assertEqual(conn.execute("SELECT count(*) FROM bridge_release WHERE delivered_at IS NOT NULL").fetchone()[0],1)
