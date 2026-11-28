"""Cross-language Workshop rehearsal: real local and cloud SQL, fake HTTPS."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_showroom_feedback as local_fixture
import cloud_role_fixture as cloud_fixture
from database_fixture import DSN
from penny.business.catalog import register
from penny.business.preview import withdraw
from penny.business.quality import review
from penny.business.quality_state import CRITERIA
from penny.progress.workshop_source import TITLE
from penny.progress.workshop_snapshot import preview,record
from penny.progress.workshop_gate import configure
from penny.progress.workshop_publisher import publish_once
from penny.scheduler.storage_db import locked

RUNNER=Path(__file__).parent/"web"/"workshop_rehearsal.mjs"


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
class WorkshopRehearsal(local_fixture.FeedbackFixture):
    def setUp(self):
        super().setUp()
        self.cloud=cloud_fixture.CloudRoleFixture()
        self.addCleanup(self.cloud.doCleanups)
        self.cloud.setUp()
        self.cloud.call("owner","UPDATE workshop_observation SET enabled=true RETURNING enabled")
        self.config=SimpleNamespace(dsn=self.dsn,host="fixture.netlify.app",key=b"x"*32)
        quality=review(self.dsn,self.task,source_ref="rehearsal:quality",
            expected_content_sha256=self.digest,checks={k:True for k in CRITERIA},
            revoked=False,reviewer_id=self.reviewer,evidence_ref="test:quality",
            evidence=b"synthetic quality",confirmed=True).entry_id
        product=register(self.dsn,self.task,source_ref="rehearsal:catalog",
            review_id=quality,content_sha256=self.digest,title=TITLE,
            reviewer_id=self.reviewer,evidence_ref="test:catalog",
            evidence=b"synthetic catalog",confirmed=True).entry_id
        candidate=preview(self.dsn,product,stage="preview_reviewed",preview_id=self.preview)
        self.assertIsNotNone(record(self.dsn,product,stage="preview_reviewed",
            preview_id=self.preview,source_ref="rehearsal:disclose",
            expected_digest=candidate["source_sha256"],reviewer_id=self.reviewer,
            evidence_ref="test:disclose",evidence=b"synthetic disclosure",confirmed=True))

    def run_node(self,value):
        env=os.environ|{"PENNY_REHEARSAL_SUFFIX":self.cloud.schema.removeprefix("mailbox_"),
                        "PENNY_REHEARSAL_PYTHON":sys.executable}
        result=subprocess.run(["node",str(RUNNER)],input=json.dumps(value),text=True,
            capture_output=True,env=env,timeout=20,check=True)
        return json.loads(result.stdout)

    def transport(self,*args,**kwargs):
        # Substitute only the connection: real wire signing and reply checks run.
        test=self
        class Connection:
            def request(self,method,path,body,headers):
                test.assertEqual(method,"POST")
                test.assertEqual(path,"/api/v1/bridge/workshop")
                test.assertEqual(set(json.loads(body)),{"sampled_at","stage","generated_at","expires_at"})
                self.response=Response(test.run_node(dict(action="post",path=path,
                    body=body.decode("ascii"),headers=headers)))
            def getresponse(self):
                return self.response
            def close(self):
                pass
        return Connection()

    def test_reviewed_publication_expiry_and_withdrawal(self):
        self.assertTrue(configure(self.config,enabled=True,limit=2,confirmed=True))
        with patch("penny.progress.workshop_wire.PublicHTTPSConnection",side_effect=self.transport):
            self.assertEqual(publish_once(self.config,confirmed=True),"published")
            result=self.run_node({"action":"browser"})
            self.assertEqual(result["status"],200)
            self.assertEqual(result["state"]["stage"],"preview_reviewed")
            self.assertEqual(set(result["body"]),{"schema","status","product","stage",
                                               "generated_at","expires_at"})
            self.assertNotIn("synthetic",json.dumps(result["body"]))
            # Real SQL read expiry; age only the disposable cloud fixture.
            n=int(time.time())
            self.cloud.call("owner","UPDATE workshop_observation SET sampled_at=%s,received_at=%s,generated_at=%s,expires_at=%s RETURNING singleton",
                            n-121,n-121,n-130,n-21)
            expired=self.run_node({"action":"browser"})
            self.assertEqual(expired["body"],{"schema":"penny-workshop-v1","status":"unavailable"})
            self.assertTrue(withdraw(self.dsn,self.preview,reviewer_id=self.reviewer,
                evidence_ref="test:withdraw",evidence=b"synthetic withdrawal",confirmed=True))
            with locked(self.dsn) as (conn,_,now):
                conn.execute("UPDATE workshop_delivery_control SET not_before=0")
            self.assertEqual(publish_once(self.config,confirmed=True),"published")
            self.assertEqual(self.cloud.call("owner","SELECT stage FROM workshop_observation"),
                             [("unavailable",)])
            self.assertEqual(self.run_node({"action":"browser"})["state"]["status"],"unavailable")
            with locked(self.dsn) as (conn,_,now):
                conn.execute("UPDATE workshop_delivery_control SET not_before=0")
            self.assertEqual(publish_once(self.config,confirmed=True),"budget_exhausted")
