"""All command output synthetic; never access live SSH or sockets."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from penny.runtime.security_audit import audit_security
from penny.runtime.security_audit_state import DesktopScope,ssh_findings,listener_findings,SSH_POLICY


class SecurityAuditTests(unittest.TestCase):
    def setUp(self):
        self.scope=DesktopScope("maker","192.168.1.20","192.168.1.30","desktop")
        self.good="\n".join(k+" "+next(iter(v)) for k,v in SSH_POLICY.items())

    def test_listener_classification(self):
        rows=listener_findings("LISTEN 0 128 127.0.0.1:5432 0.0.0.0:*\n"
            "LISTEN 0 128 [::]:11434 [::]:*\nLISTEN 0 128 192.168.1.30:22 0.0.0.0:*",
            {5432,11434},22)
        self.assertEqual(rows,[{"port":22,"binding":"nonloopback","category":"ssh_candidate"},
            {"port":5432,"binding":"loopback","category":"protected_port"},
            {"port":11434,"binding":"wildcard","category":"protected_port"}])
        with self.assertRaises(ValueError):
            listener_findings("unexpected format",{5432},22)

    def test_scope_and_missing_or_duplicate_policy(self):
        for scope in (DesktopScope("root","192.168.1.2","192.168.1.3","desktop"),
                      DesktopScope("maker","8.8.8.8","192.168.1.3","desktop"),
                      DesktopScope("maker","192.168.1.2","192.168.1.3","a,user=root")):
            with self.assertRaises(ValueError):
                scope.connection_spec()
        self.assertEqual(ssh_findings("")["passwordauthentication"],"missing")
        self.assertEqual(ssh_findings("passwordauthentication yes")["passwordauthentication"],"review_required")
        with self.assertRaises(ValueError):
            ssh_findings(self.good+"\npasswordauthentication no")

    @patch("penny.runtime.security_audit.subprocess.run")
    def test_exact_read_only_commands_and_no_certification(self,run):
        run.side_effect=[SimpleNamespace(returncode=0,stdout="LISTEN 0 128 *:11434 *:*"),
                         SimpleNamespace(returncode=0,stdout=self.good)]
        result=audit_security(self.scope)
        self.assertTrue(result["listeners"]["protected_nonloopback"])
        self.assertEqual(result["ssh"]["status"],"candidate_policy_matches")
        self.assertFalse(result["certified"])
        self.assertEqual(result["desktop_source_restriction"],"not_verified")
        self.assertEqual(run.call_args_list[0].args[0],["/usr/bin/ss","-H","-lnt"])
        self.assertEqual(run.call_args_list[1].args[0],["/usr/sbin/sshd","-T","-C",self.scope.connection_spec()])
        self.assertNotIn(self.scope.desktop,str(result))

    @patch("penny.runtime.security_audit.subprocess.run",side_effect=PermissionError)
    def test_failure_never_guesses_policy(self,run):
        result=audit_security(self.scope)
        self.assertEqual(result["listeners"]["status"],"unavailable")
        self.assertEqual(result["ssh"]["status"],"unavailable")
        self.assertFalse(result["certified"])
        self.assertEqual(run.call_count,2)
