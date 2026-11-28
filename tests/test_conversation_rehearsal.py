"""Real browser/gateway/bridge/queue SQL; synthetic inference and HTTPS only."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock,patch
from uuid import uuid4

import psycopg
from database_fixture import DSN,DatabaseFixture
from cloud_role_fixture import CloudRoleFixture
from penny.bridge.transport import BridgeClient
from penny.bridge.worker import run_bridge_once
from penny.bridge.release import approve_reply
from penny.scheduler.worker import run_once,WorkerResult

RUNNER=Path(__file__).parent/"web"/"conversation_rehearsal.mjs"


class Response:
    def __init__(self,result):
        self.status=result["status"]
        self.headers=result["headers"]
        self.body=io.BytesIO(result["body"].encode())

    def getheader(self,name,default=None):
        return self.headers.get(name.lower(),default)

    def read(self,size):
        return self.body.read(size)


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ConversationRehearsal(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.cloud=CloudRoleFixture()
        self.addCleanup(self.cloud.doCleanups)
        self.cloud.setUp()
        self.member=uuid4()
        self.key=str(uuid4())
        self.question="What is your mission?"
        self.client=BridgeClient("fixture.netlify.app",b"b"*32)
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE bridge_control SET enabled=true")
            conn.execute("INSERT INTO bridge_member VALUES (%s,%s,true)",(self.cloud.a,self.member))

    def node(self,value):
        env=os.environ|{"PENNY_REHEARSAL_SUFFIX":self.cloud.schema.removeprefix("mailbox_"),
                        "PENNY_REHEARSAL_PYTHON":sys.executable}
        result=subprocess.run(["node",str(RUNNER)],input=json.dumps(value),text=True,
                              capture_output=True,env=env,timeout=20,check=True)
        return json.loads(result.stdout)

    def browser(self,read=False):
        return self.node(dict(action="browser",owner=str(self.cloud.a),
                              key=self.key,question=self.question,read=read))

    def transport(self,*args,**kwargs):
        test=self
        class Connection:
            def request(self,method,path,body,headers):
                test.assertEqual(method,"POST")
                self.response=Response(test.node(dict(action="bridge",path=path,
                    body=body.decode("utf-8"),headers=headers)))
            def getresponse(self):
                return self.response
            def close(self):
                pass
        return Connection()

    def tick(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE bridge_control SET not_before=0")
        return run_bridge_once(self.dsn,self.client).status

    def test_reviewed_reply_reaches_only_its_member(self):
        first=self.browser()
        self.assertEqual(first["submitted"]["status"],"accepted")
        from uuid import UUID
        question=UUID(first["submitted"]["id"])
        self.assertFalse(first["cleared"]["signedIn"])
        with patch("penny.bridge.transport.PublicHTTPSConnection",side_effect=self.transport):
            self.assertEqual(self.tick(),"admitted")
            self.assertEqual(self.tick(),"acknowledged")
            brain=Mock()
            draft="Financially underfunded. Sarcastically overqualified."
            brain.generate.return_value=draft
            self.assertEqual(run_once(self.store,brain),WorkerResult.COMPLETED)
            self.assertEqual(self.tick(),"waiting_review")
            pending=self.browser(read=True)
            self.assertEqual(pending["observed"]["status"],"locally_accepted")
            self.assertIsNone(pending["observed"]["text"])
            self.assertTrue(approve_reply(self.dsn,question,reviewer_id=uuid4(),expected_text=draft))
            self.assertEqual(self.tick(),"delivered")
            result=self.browser(read=True)
            self.assertEqual(result["observed"]["status"],"answered")
            self.assertEqual(result["observed"]["text"],draft)
            self.assertIsNone(result["cleared"]["text"])
            foreign=self.node(dict(action="foreign",owner=str(self.cloud.b),id=str(question)))
            self.assertEqual(foreign["status"],404)
            self.assertNotIn(draft,foreign["body"])
            brain.generate.assert_called_once()
            self.assertEqual(brain.generate.call_args.args[0],self.question)
            with psycopg.connect(self.dsn) as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0],1)
