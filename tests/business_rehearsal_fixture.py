"""Synthetic business cycle using configured restricted inference credentials."""
import json
import time
from hashlib import sha256
from unittest.mock import Mock
from uuid import uuid4

import psycopg
from penny.business.draft_admission import submit_draft
from penny.business.draft_intake import draft_status
from penny.business.promote import promote
from penny.business.store import status
from penny.business.review import advance
from penny.business.state import Action
from penny.business.workshop_admission import submit_prototype
from penny.business.workshop_intake import read_artifact
from penny.business.quality import review,quality_status
from penny.business.quality_state import CRITERIA
from penny.business.brand import approve as approve_brand
from penny.business.edition import build_private
from penny.business.preview import approve as approve_preview,read_preview,withdraw
from penny.auth.session import issue_session
from penny.community.feedback import submit_feedback
from penny.community.feedback_review import review_feedback
from penny.community.feedback_summary import feedback_summary
from penny.runtime.inference import inference_tick
from penny.runtime.operator_control import start,stop
from test_printable import png_fixture


def rehearse_business(case,operator,worker):
    """All evidence and approvals are test fixtures, never production attestations."""
    reviewer=uuid4()
    proposal=json.dumps(dict(category="digital_product",title="Synthetic packing checklist",
        hypothesis="Three prototype checks pass",metric="prototype_checks_passed",target=3,
        duration_seconds=600,additional_cash_cents=0))
    product=json.dumps(dict(title="Synthetic packing checklist",instructions="Review each item.",
        items=["Pack documents","Check weather","Pack essentials"]))
    evidence=b"synthetic test evidence only"
    brain=Mock()
    # No real model, remote network request, payment or artifact publication.
    case.assertTrue(start(operator,"inference",confirmed=True))
    task=submit_draft(operator,key="rehearsal",brief="Synthetic checklist",reviewer_id=reviewer)
    case.assertEqual(task.status,"accept")
    brain.generate.return_value=proposal
    case.assertEqual(inference_tick(worker,brain),"completed")
    case.assertEqual(draft_status(operator,task.task_id)["status"],"quarantined")
    with psycopg.connect(operator) as conn:
        case.assertEqual(conn.execute("SELECT count(*) FROM business_opportunity").fetchone()[0],0)
    opp=promote(operator,task.task_id,expected_result_sha256=sha256(proposal.encode()).hexdigest(),
        evidence_ref="test:proposal",evidence=evidence,reviewer_id=reviewer,
        review_until=int(time.time())+3600,confirmed=True).entry_id
    case.assertEqual(status(operator,opp)["status"],"proposed")
    decision=dict(expected_proposal_sha256=sha256(evidence).hexdigest(),
        evidence_ref="test:decision",evidence=evidence,reviewer_id=reviewer,confirmed=True)
    case.assertFalse(advance(operator,opp,action=Action.START,**decision))
    for action in (Action.APPROVE,Action.START):
        case.assertTrue(advance(operator,opp,action=action,**decision))
    receipt=submit_prototype(operator,opp,key="rehearsal",reviewer_id=reviewer)
    case.assertEqual(receipt.status,"accept")
    brain.generate.return_value=product
    case.assertEqual(inference_tick(worker,brain),"completed")
    artifact=read_artifact(operator,receipt.task_id)["artifact"]
    digest=artifact["content_sha256"]
    case.assertEqual(quality_status(operator,receipt.task_id)["status"],"unreviewed")
    quality=review(operator,receipt.task_id,source_ref="test:quality",
        expected_content_sha256=digest,checks={k:True for k in CRITERIA},revoked=False,
        reviewer_id=reviewer,evidence_ref="test:quality",evidence=evidence,confirmed=True)
    artwork=png_fixture()
    edition_args=dict(review_id=quality.entry_id,source_sha256=digest,
                      brand_version="synthetic-v1",artwork=artwork)
    case.assertIsNone(build_private(operator,receipt.task_id,**edition_args))
    case.assertTrue(approve_brand(operator,"synthetic-v1",artwork=artwork,
        expected_sha256=sha256(artwork).hexdigest(),reviewer_id=reviewer,
        rights_ref="test:art",evidence=evidence,confirmed=True))
    edition=build_private(operator,receipt.task_id,**edition_args)
    case.assertEqual(sha256(edition.content).hexdigest(),edition.edition_sha256)
    case.assertFalse(edition.manifest()["commercial_release_authorized"])
    preview=approve_preview(operator,receipt.task_id,source_ref="test:preview",
        artifact_sha256=digest,title="Penny synthetic preview",preview_text="Review a sample item.",
        reviewer_id=reviewer,evidence_ref="test:preview",evidence=evidence,
        expires_at=int(time.time())+300,confirmed=True).entry_id
    projection=read_preview(operator,preview)
    case.assertFalse(projection["commercial_release_authorized"])
    case.assertNotIn("task_id",projection)
    case.assertNotIn(artifact["content"],str(projection))
    for _ in range(5):
        member=issue_session(operator,uuid4()).token
        rating=submit_feedback(operator,member,preview_id=preview,
            preview_sha256=projection["preview_sha256"],key="rate",
            usefulness=4,purchase_interest="maybe")
        case.assertEqual(rating.status,"accepted")
        case.assertTrue(review_feedback(operator,rating.feedback_id,
            expected_preview_sha256=projection["preview_sha256"],expected_usefulness=4,
            expected_interest="maybe",verdict="eligible",reason="valid_feedback",
            reviewer_id=reviewer))
    summary=feedback_summary(operator,preview)
    case.assertEqual(summary["eligible_count"],5)
    case.assertFalse(summary["commercial_authority"])
    case.assertEqual(brain.generate.call_count,2)
    case.assertTrue(withdraw(operator,preview,reviewer_id=reviewer,
        evidence_ref="test:withdraw",evidence=evidence,confirmed=True))
    case.assertIsNone(read_preview(operator,preview))
    case.assertIsNone(feedback_summary(operator,preview))
    case.assertTrue(stop(operator))
    case.assertEqual(inference_tick(worker,brain),"paused")
    with psycopg.connect(operator) as conn:
        case.assertEqual(conn.execute("SELECT count(*) FROM vault_entry").fetchone()[0],0)
        case.assertEqual(conn.execute("SELECT count(*) FROM work_task").fetchone()[0],2)
        case.assertEqual(conn.execute("SELECT paused FROM scheduler_control").fetchone()[0],True)
