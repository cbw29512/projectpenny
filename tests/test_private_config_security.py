"""Configuration boundary regression tests; no DB/network connection."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from penny.runtime.config import load_config

DSN="host=127.0.0.1 dbname=penny user=penny_runtime password=fixture"


class PrivateConfigSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"config.json"
        self.env=patch.dict(os.environ,{},clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def write(self,value):
        self.path.write_text(json.dumps(value))
        self.path.chmod(0o600)

    def test_duplicate_and_non_utf8_json_refused(self):
        self.path.write_text('{"dsn":"'+DSN+'","dsn":"'+DSN+'"}')
        self.path.chmod(0o600)
        with self.assertRaises(ValueError):
            load_config(self.path,"operator")
        self.path.write_bytes(b"\xff")
        with self.assertRaises(ValueError):
            load_config(self.path,"operator")

    def test_environment_cannot_override_loopback_or_credentials(self):
        self.write({"dsn":DSN})
        for name in ("PGHOSTADDR","PGSERVICE","PGOPTIONS","PGPASSFILE","PGPASSWORD","PGPORT","PGSSLMODE"):
            with self.subTest(name=name),patch.dict(os.environ,{name:"fixture"}):
                with self.assertRaises(PermissionError):
                    load_config(self.path,"operator")
        self.assertEqual(load_config(self.path,"operator").dsn,DSN)

    def test_parent_permissions_and_hardlink(self):
        self.write({"dsn":DSN})
        self.path.parent.chmod(0o777)
        with self.assertRaises(PermissionError):
            load_config(self.path,"operator")
        self.path.parent.chmod(0o700)
        other=self.path.parent/"alias"
        os.link(self.path,other)
        with self.assertRaises(PermissionError):
            load_config(self.path,"operator")
        other.unlink()
        self.assertEqual(load_config(self.path,"operator").dsn,DSN)

    def test_parent_symlink_refused(self):
        self.write({"dsn":DSN})
        target=self.path.parent/"real"
        target.mkdir(mode=0o700)
        self.path.rename(target/"config.json")
        link=self.path.parent/"link"
        link.symlink_to(target,target_is_directory=True)
        with self.assertRaises(OSError):
            load_config(link/"config.json","operator")

    def test_invalid_ports_and_outbound_config(self):
        for port in ("0","65536","1,2","-1"):
            self.write({"dsn":DSN+" port="+port})
            with self.assertRaises(ValueError):
                load_config(self.path,"operator")
        base={"dsn":DSN,"host":"penny.netlify.app","bridge_key_hex":"ab"*32}
        for delta in ({"host":"localhost"},{"bridge_key_hex":"ab "*32},
                      {"bridge_key_hex":"ab"*65},{"bridge_key_hex":"ab"*31}):
            self.write({**base,**delta})
            with self.assertRaises(ValueError):
                load_config(self.path,"bridge")
        self.write(base)
        self.assertEqual(load_config(self.path,"bridge").key,b"\xab"*32)
