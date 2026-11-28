"""Evidence, ownership, fairness and revocation tests with disposable PostgreSQL."""
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from database_fixture import DSN, DatabaseFixture
from penny.auth.session import issue_session
from penny.guardian.state import Decision
from penny.recognition.admin import record_outcome, verify_request
from penny.recognition.member import request_credit, list_credit, withdraw_credit
from penny.recognition.state import Outcome, Role, CONSENT_VERSION


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class RecognitionTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.reviewer = uuid4()

    def outcome(self,verdict=Outcome.IMPROVED,ref="trial/1",evidence=b"measured evidence"):
        return record_outcome(self.dsn,outcome_ref=ref,verdict=verdict,
                              evidence=evidence,reviewer_id=self.reviewer)

    def member(self):
        member = uuid4()
        return member,issue_session(self.dsn,member).token

    def request(self,token,outcome,role=Role.IDEA):
        return request_credit(self.dsn,token,outcome,role,accepted_version=CONSENT_VERSION)

    def verify(self,request):
        return verify_request(self.dsn,request,reviewer_id=self.reviewer,
                              evidence_ref="attribution/1",evidence=b"verified contribution")

    def test_outcome_deduplication_and_conflict(self):
        outcome = self.outcome()
        self.assertEqual(self.outcome(),outcome)
        with self.assertRaises(ValueError):
            self.outcome(Outcome.UNSUCCESSFUL)
        with self.assertRaises(ValueError):
            self.outcome(evidence=b"changed")

    def test_consent_and_independent_review_required(self):
        _,token = self.member()
        outcome = self.outcome()
        with self.assertRaises(ValueError):
            request_credit(self.dsn,token,outcome,Role.IDEA,accepted_version="old")
        self.assertFalse(self.verify(uuid4()))
        request = self.request(token,outcome)
        self.assertEqual(self.request(token,outcome),request)
        self.assertEqual(list_credit(self.dsn,token),())
        self.assertTrue(self.verify(request))
        self.assertFalse(self.verify(request))
        self.assertEqual(len(list_credit(self.dsn,token)),1)

    def test_equal_credit_multiple_members_regardless_of_payment(self):
        free,a = self.member()
        paid,b = self.member()
        with psycopg.connect(self.dsn) as conn:
            conn.execute("INSERT INTO scheduler_entitlement VALUES (%s,6,9999999999)",(paid,))
        outcome = self.outcome()
        ra,rb = self.request(a,outcome),self.request(b,outcome)
        self.assertTrue(self.verify(ra))
        self.assertTrue(self.verify(rb))
        first,second = list_credit(self.dsn,a)[0],list_credit(self.dsn,b)[0]
        self.assertEqual(first.message,second.message)
        self.assertEqual(first.request_id,ra)
        self.assertEqual(second.request_id,rb)
        self.assertFalse(withdraw_credit(self.dsn,a,rb))

    def test_outcomes_not_misrepresented(self):
        _,token = self.member()
        for verdict,phrase in ((Outcome.UNSUCCESSFUL,"did not succeed"),
                               (Outcome.INCONCLUSIVE,"inconclusive")):
            outcome = self.outcome(verdict,ref=verdict.value)
            self.assertTrue(self.verify(self.request(token,outcome)))
            record = next(r for r in list_credit(self.dsn,token) if r.outcome_id==outcome)
            self.assertIn(phrase,record.message)

    def test_withdrawal_during_identity_drift_and_no_resurrection(self):
        _,token = self.member()
        outcome = self.outcome()
        request = self.request(token,outcome)
        self.assertTrue(self.verify(request))
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertTrue(withdraw_credit(self.dsn,token,request))
        self.assertFalse(self.verify(request))
        new = self.request(token,outcome)
        self.assertNotEqual(new,request)
        self.assertEqual(list_credit(self.dsn,token),())
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM contribution_outcome").fetchone()[0],1)
            self.assertEqual(conn.execute("SELECT count(*) FROM contribution_recognition").fetchone()[0],0)

    def test_invalid_consent_chronology_cannot_receive_credit(self):
        _,token = self.member()
        outcome = self.outcome()
        request = self.request(token,outcome)
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE contribution_request SET requested_at=requested_at+86400 WHERE id=%s",(request,))
        self.assertIsNone(self.request(token,outcome))
        self.assertFalse(self.verify(request))
        self.assertEqual(list_credit(self.dsn,token),())
        self.assertTrue(withdraw_credit(self.dsn,token,request))

    def test_future_recognition_not_displayed(self):
        _,token = self.member()
        request = self.request(token,self.outcome())
        self.assertTrue(self.verify(request))
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE contribution_recognition SET recorded_at=recorded_at+86400 WHERE request_id=%s",(request,))
        self.assertEqual(list_credit(self.dsn,token),())

    def test_guardian_and_session_denial(self):
        _,token = self.member()
        outcome = self.outcome()
        request = self.request(token,outcome)
        with patch("penny.recognition.admin.authorize",return_value=Decision(False,"denied")):
            self.assertFalse(self.verify(request))
            self.assertIsNone(self.outcome(ref="blocked"))
        with self.assertRaises(PermissionError):
            list_credit(self.dsn,"a"*43)
        self.assertEqual(list_credit(self.dsn,token),())
