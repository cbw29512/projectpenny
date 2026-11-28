import subprocess
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from penny.brain.local import LocalBrain
from penny.scheduler.storage_state import Claim
from penny.scheduler.worker import WorkerResult, run_once


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.store = Mock(dsn="test-only")
        self.claim = Claim(uuid4(), uuid4(), "hello", 1120)
        self.store.claim.return_value = self.claim
        self.brain = Mock()
        self.brain.generate.return_value = "Hello from Penny."
        self.finish = Mock(return_value=True)

    def run_worker(self):
        return run_once(self.store, self.brain, finish=self.finish, clock=lambda: 1000)

    def test_identity_failure_does_not_claim_or_call_brain(self):
        with patch("penny.brain.identity.SYSTEM_PROMPT", "changed"):
            self.assertEqual(self.run_worker(), WorkerResult.BLOCKED)
        self.store.claim.assert_not_called()
        self.brain.generate.assert_not_called()
        self.finish.assert_not_called()

    def test_guardian_rechecks_identity_after_inference(self):
        with patch("penny.guardian.policy.identity_matches", side_effect=[True, False]):
            self.assertEqual(self.run_worker(), WorkerResult.BLOCKED)
        self.brain.generate.assert_called_once()
        self.finish.assert_not_called()

    def test_idle_no_model_call(self):
        self.store.claim.return_value = None
        self.assertEqual(self.run_worker(), WorkerResult.IDLE)
        self.brain.generate.assert_not_called()
        self.finish.assert_not_called()

    def test_success_one_claim_and_fenced_finish(self):
        self.assertEqual(self.run_worker(), WorkerResult.COMPLETED)
        self.store.claim.assert_called_once()
        self.brain.generate.assert_called_once_with("hello", 90.0)
        self.finish.assert_called_once_with(
            "test-only", self.claim.task_id, self.claim.fence,
            success=True, result="Hello from Penny.",
        )

    def test_timeout_does_not_release_or_retry(self):
        self.brain.generate.side_effect = TimeoutError()
        self.assertEqual(self.run_worker(), WorkerResult.BLOCKED)
        self.brain.generate.assert_called_once()
        self.finish.assert_not_called()

    def test_no_budget_no_inference(self):
        self.store.claim.return_value = Claim(uuid4(), uuid4(), "hello", 1004)
        self.assertEqual(self.run_worker(), WorkerResult.BLOCKED)
        self.brain.generate.assert_not_called()
        self.finish.assert_not_called()

    def test_invalid_output_no_finish(self):
        self.brain.generate.return_value = ""
        self.assertEqual(self.run_worker(), WorkerResult.BLOCKED)
        self.finish.assert_not_called()

    def test_lost_fence(self):
        self.finish.return_value = False
        self.assertEqual(self.run_worker(), WorkerResult.BLOCKED)
        self.finish.assert_called_once()

    def test_late_result(self):
        ticks = iter([1000,1121])
        self.assertEqual(run_once(self.store,self.brain,finish=self.finish,clock=lambda:next(ticks)),
                         WorkerResult.BLOCKED)
        self.finish.assert_not_called()

    def test_database_failure_no_retry(self):
        self.finish.side_effect = RuntimeError()
        self.assertEqual(self.run_worker(), WorkerResult.BLOCKED)
        self.finish.assert_called_once()

    @patch("penny.brain.local.subprocess.run")
    def test_parent_wall_timeout(self, call):
        call.side_effect = subprocess.TimeoutExpired("child", 10)
        with self.assertRaises(RuntimeError):
            LocalBrain().generate("hello", 10)
        call.assert_called_once()
        self.assertEqual(call.call_args.kwargs["timeout"], 10)
