"""Local operator boundaries; no production credentials or real product data."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from penny.runtime.private_evidence import read_evidence
from penny.runtime.workshop import main
from penny.business.quality_state import CRITERIA,PrivateExport


class EvidenceTests(unittest.TestCase):
    def test_private_file_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"evidence"
            path.write_bytes(b"synthetic")
            path.chmod(0o600)
            self.assertEqual(read_evidence(path),b"synthetic")
            link=Path(folder)/"link"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                read_evidence(link)
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                read_evidence(path)
            path.chmod(0o600)
            path.write_bytes(b"x"*16385)
            with self.assertRaises(PermissionError):
                read_evidence(path)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.task=uuid4()
        self.reviewer=uuid4()
        self.digest="a"*64

    def run_cli(self,args):
        out=io.StringIO()
        with patch("penny.runtime.workshop.load_config",return_value=SimpleNamespace(dsn="fixture")),contextlib.redirect_stdout(out):
            code=main(["--config","private.json",*args])
        return code,out.getvalue()

    def review_args(self):
        args=["review",str(self.task),"--digest",self.digest,"--source-ref","review:1",
              "--reviewer-id",str(self.reviewer),"--evidence-ref","private:review",
              "--evidence-file","private.txt"]
        for criterion in CRITERIA:
            args.extend(["--"+criterion,"fail" if criterion=="accuracy" else "pass"])
        return args

    @patch("penny.runtime.workshop.review")
    @patch("penny.runtime.workshop.read_evidence")
    def test_confirmation_and_each_criterion(self,read,review):
        code,_=self.run_cli(self.review_args())
        self.assertEqual(code,1)
        read.assert_not_called()
        review.assert_not_called()
        read.return_value=b"synthetic"
        review.return_value=SimpleNamespace(entry_id=uuid4(),replayed=False)
        code,out=self.run_cli(self.review_args()+["--confirm"])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out)["review_id"],str(review.return_value.entry_id))
        self.assertFalse(review.call_args.kwargs["checks"]["accuracy"])
        self.assertTrue(review.call_args.kwargs["confirmed"])

    @patch("penny.runtime.workshop.inspect")
    def test_inspect_escapes_untrusted_terminal_text(self,inspect):
        inspect.return_value={"artifact":{"content":"\x1b[31m\u202e"}}
        code,out=self.run_cli(["inspect",str(self.task)])
        self.assertEqual(code,0)
        self.assertNotIn("\x1b",out)
        self.assertNotIn("\u202e",out)
        self.assertEqual(json.loads(out),inspect.return_value)

    @patch("penny.runtime.workshop.export_private")
    def test_export_exact_bytes_no_json_or_logging_on_stdout(self,export):
        export.return_value=PrivateExport("test.txt","text/plain",self.digest,b"synthetic\n")
        stream=io.BytesIO()
        out=io.TextIOWrapper(stream,encoding="utf-8")
        args=["--config","private.json","export",str(self.task),
              "--review-id",str(uuid4()),"--digest",self.digest]
        with patch("penny.runtime.workshop.load_config",return_value=SimpleNamespace(dsn="fixture")),contextlib.redirect_stdout(out):
            self.assertEqual(main(args),0)
        self.assertEqual(stream.getvalue(),b"synthetic\n")

    @patch("penny.runtime.workshop.export_private")
    def test_denied_export_writes_no_bytes(self,export):
        export.return_value=None
        code,out=self.run_cli(["export",str(self.task),"--review-id",str(uuid4()),"--digest",self.digest])
        self.assertEqual(code,1)
        self.assertEqual(out,"")
