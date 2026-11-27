"""Revenue-path storage boundary; disposable PostgreSQL, fake model only."""
import json
import time
import unittest
from hashlib import sha256
from unittest.mock import Mock
from uuid import uuid4

import psycopg
from psycopg import sql
from database_fixture import DSN,DatabaseFixture
from penny.business.draft_admission import submit_draft
from penny.business.draft_intake import draft_status
from penny.business.draft_parse import parse_draft
from penny.business.checklist import render_checklist
from penny.business.state import Category,Metric,Action
from penny.business.store import stage
from penny.business.review import advance
from penny.business.workshop_admission import submit_prototype
from penny.business.workshop_intake import read_artifact
from penny.runtime.inference import inference_tick
from penny.runtime.claim_store import ScopedClaimStore
from penny.runtime.inference_db import gate_call
from penny.runtime.operator_control import stop

VALID=dict(category="digital_product",title="Private checklist",
           hypothesis="Five prototype checks pass",metric="prototype_checks_passed",
           target=5,duration_seconds=600,additional_cash_cents=0)
RAW=json.dumps(dict(title="Packing checklist",instructions="Review each item.",
                    items=["Pack documents","Check weather","Pack essentials"]))


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ScopedRevenueTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer=uuid4()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET enabled=true")

    def test_proposal_parser_and_checklist_parity(self):
        with psycopg.connect(self.dsn) as conn:
            for value in (VALID,{**VALID,"target":True},{**VALID,"target":1.0},
                          {**VALID,"additional_cash_cents":1},{**VALID,"duration_seconds":0},
                          {**VALID,"title":"\u0000"},{**VALID,"approved":True}):
                raw=json.dumps(value)
                draft=parse_draft(raw)
                rows=conn.execute("SELECT * FROM penny_private_parse_business(%s)",(raw,)).fetchall()
                expected=[] if draft is None else [(draft.category.value,draft.title,draft.hypothesis,
                    draft.metric.value,draft.target,draft.duration_seconds,draft.additional_cash_cents)]
                self.assertEqual(rows,expected)
            raw=json.dumps(VALID).replace('"target": 5','"target": 5, "target": 6')
            self.assertEqual(conn.execute("SELECT * FROM penny_private_parse_business(%s)",(raw,)).fetchall(),[])
            for raw in (RAW,'{}','{"title":"a","title":"b"}',
                        json.dumps(dict(title="X",instructions="Y",items=["a","A","b"])),
                        json.dumps(dict(title="X",instructions="Y",items=["a","b","c"],tool="publish"))):
                self.assertEqual(conn.execute("SELECT penny_private_render_checklist(%s)",(raw,)).fetchone()[0],
                                 render_checklist(raw))
            # Explicit conservative limitation of SQL folding, not silent parity.
            raw=json.dumps(dict(title="X",instructions="Y",items=["café","b","c"]))
            self.assertIsNotNone(render_checklist(raw))
            self.assertIsNone(conn.execute("SELECT penny_private_render_checklist(%s)",(raw,)).fetchone()[0])

    def proposal(self,key="one"):
        r=submit_draft(self.dsn,key=key,brief="Explore a packing checklist",reviewer_id=self.reviewer)
        self.assertEqual(r.status,"accept")
        return r

    def run_model(self,raw):
        brain=Mock()
        brain.generate.return_value=raw
        self.assertEqual(inference_tick(self.dsn,brain),"completed")

    def test_proposal_no_automatic_opportunity_or_spend(self):
        r=self.proposal()
        self.run_model(json.dumps(VALID))
        result=draft_status(self.dsn,r.task_id)
        self.assertEqual(result["status"],"quarantined")
        self.assertEqual(result["authorized_cents"],0)
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM business_opportunity").fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT count(*) FROM vault_entry").fetchone()[0],0)

    def workshop(self):
        evidence=b"synthetic reviewed opportunity"
        key=stage(self.dsn,source_ref="scoped-workshop",category=Category.DIGITAL_PRODUCT,
            title="Packing checklist",hypothesis="Usable checklist",metric=Metric.PROTOTYPE_CHECKS_PASSED,
            target=3,duration_seconds=600,additional_cash_cents=0,evidence_ref="private:test",
            evidence=evidence,reviewer_id=self.reviewer,review_until=int(time.time())+3600).entry_id
        for action in (Action.APPROVE,Action.START):
            self.assertTrue(advance(self.dsn,key,action=action,
                expected_proposal_sha256=sha256(evidence).hexdigest(),evidence_ref="private:review",
                evidence=b"synthetic decision",reviewer_id=self.reviewer,confirmed=True))
        r=submit_prototype(self.dsn,key,key="one",reviewer_id=self.reviewer)
        self.assertEqual(r.status,"accept")
        return r

    def test_workshop_private_prototype_and_hashes(self):
        r=self.workshop()
        self.run_model(RAW)
        result=read_artifact(self.dsn,r.task_id)
        self.assertEqual(result["status"],"private_prototype")
        self.assertEqual(result["artifact"]["content"],render_checklist(RAW))
        self.assertEqual(result["artifact"]["content_sha256"],
                         sha256(render_checklist(RAW).encode()).hexdigest())
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT result_sha256 FROM workshop_artifact").fetchone()[0],
                             sha256(RAW.encode()).hexdigest())

    def test_stop_during_work_preserves_raw_but_no_artifact(self):
        r=self.workshop()
        token=gate_call(self.dsn,"begin")["token"]
        claim=ScopedClaimStore(self.dsn,token).claim()
        self.assertEqual(claim.task_id,r.task_id)
        self.assertTrue(stop(self.dsn))
        with psycopg.connect(self.dsn) as conn:
            result=conn.execute("SELECT penny_inference_complete_draft(%s,%s,%s,%s)",
                                (token,claim.task_id,claim.fence,RAW)).fetchone()[0]
            self.assertEqual(result,"completed")
        self.assertEqual(read_artifact(self.dsn,r.task_id),{"status":"not_staged","artifact":None})
