"""Synthetic child environment and output checks; never call Ollama."""
import json
import os
import unittest
from unittest.mock import patch
from penny.brain.local import LocalBrain


class LocalChildTests(unittest.TestCase):
    @patch("penny.brain.local.subprocess.run")
    def test_child_does_not_inherit_parent_credentials(self,run):
        run.return_value.stdout=json.dumps("Draft")
        with patch.dict(os.environ,{"PGPASSWORD":"synthetic","PYTHONPATH":"/untrusted",
                                    "HTTPS_PROXY":"http://example.invalid",
                                    "LD_PRELOAD":"/untrusted.so","PENNY_KEY":"synthetic"}):
            self.assertEqual(LocalBrain().generate("Work",30),"Draft")
        args,kwargs=run.call_args
        self.assertEqual(kwargs["env"],{"PATH":"/usr/bin:/bin","LC_ALL":"C.UTF-8"})
        self.assertEqual(args[0][1:],["-E","-s","-B","-m","penny.brain.transport"])
        self.assertEqual(kwargs["timeout"],30)

    @patch("penny.brain.local.subprocess.run")
    def test_invalid_child_result_fails_closed(self,run):
        for output in (json.dumps({"content":"Draft"}),json.dumps(" "),
                       json.dumps("x"*16001),json.dumps("bad\x00"),"x"*192003):
            with self.subTest(size=len(output)):
                run.return_value.stdout=output
                with self.assertRaises(RuntimeError):
                    LocalBrain().generate("Work",30)
