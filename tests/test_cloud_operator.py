"""Cloud operator interface: synthetic credentials, no provider connection."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch,Mock
from netlify.security.credentials import validate_dsn
from netlify.security.operator_config import load
from netlify.security.operator import main,apply
from netlify.security.audit import AuditResult
from netlify.security.manifest import release_plan
from netlify.security.roles import SCOPES

DSN="host=db.example dbname=cloud user=installer password=fixture sslmode=verify-full sslrootcert=/private/ca.pem"


class OperatorTests(unittest.TestCase):
    def test_plan_requires_no_credentials(self):
        out=io.StringIO()
        with patch("netlify.security.operator.load") as load_mock,contextlib.redirect_stdout(out):
            self.assertEqual(main(["plan"]),0)
        load_mock.assert_not_called()
        self.assertEqual(len(json.loads(out.getvalue())["migrations"]),13)

    @patch("netlify.security.operator.load")
    @patch("netlify.security.operator.apply")
    def test_wrong_digest_or_unconfirmed_never_loads_credentials(self,apply_mock,load_mock):
        for digest,confirm in (("0"*64,True),(release_plan()[0],False)):
            args=["install","--config","fixture","--release-sha256",digest]
            self.assertEqual(main(args+(["--confirm"] if confirm else [])),1)
        apply_mock.assert_not_called()
        load_mock.assert_not_called()

    @patch("netlify.security.operator_config.read_config")
    def test_config_exact_roles_and_secret_repr(self,read):
        data=dict(database="cloud",login="installer",dsn=DSN,owner="owner",
                  roles={scope:scope+"_role" for scope in SCOPES})
        read.return_value=data
        self.assertNotIn("password",repr(load("fixture","install")))
        data["roles"]["member"]="owner"
        with self.assertRaises(ValueError):
            load("fixture","install")

    @patch("netlify.security.operator.load")
    @patch("netlify.security.operator.probe_login")
    def test_probe_reports_only_scope_and_checks(self,probe,load_mock):
        load_mock.return_value=Mock(dsn=DSN,database="cloud",login="installer",scope="member")
        probe.return_value=AuditResult(False,("database_temp",))
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["probe","--config","fixture"]),1)
        self.assertNotIn("password",out.getvalue())
        self.assertFalse(json.loads(out.getvalue())["production_certified"])

    def test_unsafe_connection_options_refused(self):
        for dsn in (DSN.replace("verify-full","require"),DSN+" options='-c role=owner'",
                    DSN.replace("dbname=cloud","dbname=penny"),DSN.replace("db.example","/tmp")):
            with self.assertRaises((ValueError,PermissionError)):
                validate_dsn(dsn,database="cloud",role="installer")

    @patch("netlify.security.operator.install_fresh")
    @patch("netlify.security.operator.psycopg.connect")
    def test_install_refuses_wrong_actual_connection(self,connect,install):
        conn=connect.return_value.__enter__.return_value
        conn.execute.return_value.fetchone.return_value=("cloud","owner","installer",True)
        config=Mock(dsn=DSN,database="cloud",login="installer")
        with self.assertRaises(PermissionError):
            apply(config,release_plan()[0])
        install.assert_not_called()
