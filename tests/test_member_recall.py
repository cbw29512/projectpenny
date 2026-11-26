"""Personal recall isolation and consent-race regression tests."""
import unittest
from unittest.mock import Mock
from uuid import uuid4

import psycopg
from memory_review_fixture import DSN, ReviewFixture
from penny.auth.member_chat import MemberChatService
from penny.auth.member_memory import MemberMemoryService
from penny.auth.session import issue_session
from penny.brain.request import render_request
from penny.memory.member_recall import recall_preferences
from penny.memory.member_state import CONSENT_VERSION
from penny.memory.recall import recall
from penny.scheduler.outcomes import complete
from penny.scheduler.worker import run_once,WorkerResult


class PersonalEnvelopeTests(unittest.TestCase):
    def test_personal_context_separate_from_business(self):
        self.assertIn("untrusted optional context",render_request({"task":"Hi","preferences":["Short answers"]}))
        for data in ({"task":"Hi","preferences":["x"*301]},
                     {"task":"Hi","preferences":["x"]*4},
                     {"task":"Hi","preferences":["x"],"memories":[]}):
            with self.assertRaises(ValueError):
                render_request(data)


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class MemberRecallTests(ReviewFixture):
    def setUp(self):
        super().setUp()
        self.chat = MemberChatService(self.store)
        self.memory = MemberMemoryService(self.dsn)

    def member(self):
        s = issue_session(self.dsn,uuid4())
        c = self.memory.opt_in(s.token,accepted_version=CONSENT_VERSION)
        return s,c

    def test_default_off_and_requires_consent(self):
        s = issue_session(self.dsn,uuid4())
        self.assertEqual(self.chat.submit(s.token,"a","Hi",use_personal_memory=True).status,
                         "memory_consent_required")
        self.assertEqual(self.chat.submit(s.token,"a","Hi").status,"accept")
        claim = self.store.claim()
        self.assertFalse(claim.personal_memory_enabled)
        self.assertEqual(recall_preferences(self.dsn,claim.task_id,claim.fence),())

    def test_only_owner_context_reaches_worker(self):
        a,ca = self.member()
        b,cb = self.member()
        item = self.memory.save(a.token,ca.epoch,"Use concise replies")
        self.memory.save(b.token,cb.epoch,"Different preference")
        self.chat.submit(a.token,"a","Hi",use_personal_memory=True)
        brain = Mock()
        brain.generate_with_preferences.return_value = "Private response"
        self.assertEqual(run_once(self.store,brain),WorkerResult.COMPLETED)
        self.assertEqual(brain.generate_with_preferences.call_args.args[2],(item,))
        brain.generate_with_memory.assert_not_called()

    def test_stale_epoch_and_forged_fence(self):
        s,c = self.member()
        self.memory.save(s.token,c.epoch,"Old preference")
        self.chat.submit(s.token,"a","Hi",use_personal_memory=True)
        self.memory.withdraw(s.token)
        c2 = self.memory.opt_in(s.token,accepted_version=CONSENT_VERSION)
        self.memory.save(s.token,c2.epoch,"New preference")
        claim = self.store.claim()
        self.assertEqual(recall_preferences(self.dsn,claim.task_id,uuid4()),())
        self.assertEqual(recall_preferences(self.dsn,claim.task_id,claim.fence),())
        self.assertEqual(recall(self.dsn,claim.task_id,claim.fence),())

    def test_deletion_after_recall_discards_result(self):
        s,c = self.member()
        item = self.memory.save(s.token,c.epoch,"Private preference")
        self.chat.submit(s.token,"a","Hi",use_personal_memory=True)
        claim = self.store.claim()
        self.assertEqual(recall_preferences(self.dsn,claim.task_id,claim.fence),(item,))
        self.assertTrue(self.memory.delete(s.token,item.id))
        self.assertFalse(complete(self.dsn,claim.task_id,claim.fence,success=True,result="Private preference"))
        with psycopg.connect(self.dsn) as conn:
            self.assertEqual(conn.execute("SELECT status,result FROM task_outcome").fetchone(),
                             ("canceled","personal memory permission changed"))

    def test_memory_choice_bound_to_idempotency_key(self):
        s,c = self.member()
        a = self.chat.submit(s.token,"a","Hi",use_personal_memory=True)
        self.assertEqual(self.chat.submit(s.token,"a","Hi",use_personal_memory=True).task_id,a.task_id)
        self.assertEqual(self.chat.submit(s.token,"a","Hi").status,"idempotency_conflict")
        self.assertEqual(self.store.submit(uuid4(),"forged","Hi",use_personal_memory=True).status,"invalid")
