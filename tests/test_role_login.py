"""Read-only service connection and CLI tests; no live credentials."""
import io
import json
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import Mock,patch

from penny.runtime.role_login import inspect_connection,probe_login
from penny.runtime.role_state import RoleAudit
from penny.runtime.role_login_cli import main


class RoleLoginTests(unittest.TestCase):
    def inspect(self,row,extra=False,audit=None):
        conn=Mock()
        conn.execute.side_effect=[Mock(fetchone=Mock(return_value=row)),
                                  Mock(fetchone=Mock(return_value=(extra,)))]
        with patch("penny.runtime.role_login.audit_role",
                   return_value=audit or RoleAudit(True,())):
            result=inspect_connection(conn,"penny_core","penny_infer","inference")
        self.assertEqual(conn.execute.call_count,2)
        self.assertTrue(all(call.args[0].lstrip().startswith("SELECT")
                            for call in conn.execute.call_args_list))
        return result

    def test_good_login(self):
        for path in (["penny_core"],["pg_catalog","penny_core"]):
            self.assertTrue(self.inspect(("penny_infer","penny_infer",path,True,
                                          False,False,False)).ready)

    def test_wrong_session_search_path_and_database_privileges(self):
        result=self.inspect(("penny_infer","owner",["public","penny_core"],
                             True,True,True,True),extra=True,
                            audit=RoleAudit(False,("direct_relation:work_task",)))
        self.assertFalse(result.ready)
        self.assertEqual(set(result.issues),{"wrong_runtime_login","unsafe_runtime_search_path",
            "database_create_or_owner","database_temp","other_application_schema_access",
            "direct_relation:work_task"})

    def test_no_login_or_wrong_role(self):
        self.assertIn("wrong_runtime_login",self.inspect(
            ("other","other",["penny_core"],False,False,False,False)).issues)

    @patch("penny.runtime.role_login.psycopg.connect",side_effect=RuntimeError("secret"))
    def test_unavailable_is_not_pass(self,connect):
        self.assertEqual(probe_login("private-dsn","penny_core","penny_infer","inference"),
                         RoleAudit(False,("login_probe_unavailable",)))

    @patch("penny.runtime.role_login.inspect_connection",return_value=RoleAudit(True,()))
    @patch("penny.runtime.role_login.psycopg.connect")
    def test_probe_sets_read_only_and_bounded_timeouts(self,connect,inspect):
        conn=connect.return_value.__enter__.return_value
        self.assertTrue(probe_login("private-dsn","penny_core","penny_infer","inference").ready)
        statements=[c.args[0] for c in conn.execute.call_args_list]
        self.assertEqual(statements,["SET TRANSACTION READ ONLY",
                                     "SET LOCAL statement_timeout='5s'",
                                     "SET LOCAL lock_timeout='5s'"])
        inspect.assert_called_once_with(conn,"penny_core","penny_infer","inference")

    @patch("penny.runtime.role_login_cli.probe_login",return_value=RoleAudit(False,("database_temp",)))
    @patch("penny.runtime.role_login_cli.load_config",return_value=SimpleNamespace(dsn="secret-dsn"))
    def test_cli_failure_and_no_secrets(self,load,probe):
        out=io.StringIO()
        with redirect_stdout(out):
            code=main(["--config","/private/inference.json","--scope","inference",
                       "--schema","penny_core","--role","penny_infer"])
        self.assertEqual(code,1)
        self.assertNotIn("secret-dsn",out.getvalue())
        self.assertFalse(json.loads(out.getvalue())["production_certified"])
