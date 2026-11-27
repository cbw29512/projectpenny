"""Read-only diagnostic tests: all external calls mocked."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from penny.brain.transport import MODEL
from penny.runtime.preflight import model_probe, unit_probe, preflight

class PreflightTests(unittest.TestCase):
    @patch("penny.runtime.preflight.http.client.HTTPConnection")
    def test_model_inventory_only(self, http):
        conn = http.return_value
        response = conn.getresponse.return_value
        response.status = 200
        response.read.return_value = json.dumps({"models":[
            {"name":MODEL,"digest":"a"*64}]}).encode()
        self.assertEqual(model_probe(), "present_unbenchmarked")
        conn.request.assert_called_once_with("GET", "/api/tags")
        conn.close.assert_called_once()
        response.read.return_value = b'{"models":[]}'
        self.assertEqual(model_probe(), "missing")

    @patch("penny.runtime.preflight.subprocess.run")
    def test_only_fixed_read_only_units(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout="LoadState=loaded\nActiveState=inactive\n")
        self.assertEqual(unit_probe("penny-inference.timer"),"inactive")
        self.assertIn("show",run.call_args.args[0])
        self.assertEqual(unit_probe("ollama.service"),"invalid")
        self.assertEqual(run.call_count,1)

    @patch("penny.runtime.preflight.unit_probe",return_value="missing")
    @patch("penny.runtime.preflight.model_probe",return_value="missing")
    @patch("penny.runtime.preflight.identity_matches",return_value=True)
    @patch("penny.runtime.preflight.load_config",side_effect=PermissionError)
    def test_independent_failures_are_not_certification(self, config, identity, model, unit):
        result = preflight("/private")
        self.assertFalse(result["certified"])
        self.assertEqual(result["configuration"]["database"]["status"],"not_checked")
        self.assertEqual(result["configuration"]["bridge"],"unavailable")
        self.assertEqual(result["model_inventory"],"missing")
        self.assertEqual(unit.call_count,4)
