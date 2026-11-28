"""Operator authorization is explicit, never a default."""
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from types import SimpleNamespace

from penny.runtime.workshop_publish import main


class WorkshopPublishCliTests(unittest.TestCase):
    @patch("penny.runtime.workshop_publish.configure",return_value=True)
    @patch("penny.runtime.workshop_publish.load_config")
    def test_enable_requires_explicit_confirmation_and_limit(self,load,configure):
        load.return_value=SimpleNamespace(dsn="fixture")
        args=["--config","private.json","enable","--daily-limit","10"]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(args),1)
            load.assert_not_called()
            self.assertEqual(main(args+["--confirm"]),0)
        load.assert_called_once_with("private.json","workshop")
        configure.assert_called_once_with(load.return_value,enabled=True,limit=10,
                                          reconciled=False,confirmed=True)

    @patch("penny.runtime.workshop_publish.publish_once",return_value="paused")
    @patch("penny.runtime.workshop_publish.load_config")
    def test_paused_publication_is_not_success(self,load,publish):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["--config","private.json","publish-once","--confirm"]),1)
        self.assertEqual(out.getvalue().strip(),"paused")
        publish.assert_called_once_with(load.return_value,confirmed=True)
