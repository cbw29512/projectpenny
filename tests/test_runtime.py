"""Runtime gate and private configuration tests; never start systemd or Ollama."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from uuid import uuid4

import psycopg
from database_fixture import DSN,DatabaseFixture
from penny.runtime.config import load_config
from penny.runtime.inference import inference_tick
from penny.scheduler.worker import WorkerResult


class ConfigTests(unittest.TestCase):
    def test_private_file_only_and_no_remote_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"config.json"
            dsn="host=127.0.0.1 dbname=penny user=penny_runtime password=synthetic"
            path.write_text(json.dumps({"dsn":dsn}))
            path.chmod(0o600)
            config=load_config(path,"inference")
            self.assertEqual(config.dsn,dsn)
            self.assertNotIn("synthetic",repr(config))
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                load_config(path,"inference")
            path.chmod(0o600)
            path.write_text(json.dumps({"dsn":dsn.replace("127.0.0.1","example.com")}))
            with self.assertRaises(ValueError):
                load_config(path,"inference")

    def test_bridge_secrets_separate_and_symlink_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"config.json"
            path.write_text(json.dumps({"dsn":"host=127.0.0.1 dbname=penny user=penny_runtime",
                "host":"penny.netlify.app","bridge_key_hex":"ab"*32}))
            path.chmod(0o600)
            self.assertEqual(len(load_config(path,"bridge").key),32)
            self.assertNotIn("abab",repr(load_config(path,"bridge")))
            with self.assertRaises(ValueError):
                load_config(path,"inference")
            link=Path(tmp)/"link"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                load_config(link,"bridge")


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class RuntimeTests(DatabaseFixture):
    def enable(self):
        with psycopg.connect(self.dsn) as conn:
            conn.execute("UPDATE inference_runtime SET enabled=true")

    def test_default_closed_and_normal_cycle(self):
        brain=Mock()
        self.store.submit(None,"business","Work")
        self.assertEqual(inference_tick(self.dsn,brain),"paused")
        brain.generate.assert_not_called()
        self.enable()
        brain.generate.return_value="Draft"
        self.assertEqual(inference_tick(self.dsn,brain),"completed")
        self.assertEqual(inference_tick(self.dsn,brain),"idle")
        brain.generate.assert_called_once()

    def test_uncertain_inference_blocks_restart(self):
        self.enable()
        self.store.submit(None,"business","Work")
        brain=Mock()
        brain.generate.side_effect=TimeoutError
        self.assertEqual(inference_tick(self.dsn,brain),"blocked")
        self.assertEqual(inference_tick(self.dsn,brain),"blocked")
        brain.generate.assert_called_once()

    def test_crash_marker_survives_restart(self):
        self.enable()
        with patch("penny.runtime.inference.run_once",side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                inference_tick(self.dsn,Mock())
        brain=Mock()
        self.assertEqual(inference_tick(self.dsn,brain),"blocked")
        brain.generate.assert_not_called()

    def test_existing_running_task_never_auto_stolen(self):
        self.enable()
        self.store.submit(uuid4(),"key","Question")
        self.assertIsNotNone(self.store.claim())
        brain=Mock()
        self.assertEqual(inference_tick(self.dsn,brain),"blocked")
        brain.generate.assert_not_called()

    def test_identity_and_pause_block(self):
        self.enable()
        brain=Mock()
        with patch("penny.brain.identity.SYSTEM_PROMPT","changed"):
            self.assertEqual(inference_tick(self.dsn,brain),"paused")
        self.store.set_paused(True)
        self.assertEqual(inference_tick(self.dsn,brain),"paused")
        brain.generate.assert_not_called()
