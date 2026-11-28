"""Static deployment contract tests; no systemd invocation or live mutation."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]/"deployment"/"isolated"
PROFILES={"inference":("penny-infer","inference"),
          "bridge":("penny-bridge","bridge"),
          "activity":("penny-project","projection")}


class IsolatedUnitTests(unittest.TestCase):
    def test_distinct_nonroot_accounts_and_read_only_release(self):
        for kind,(user,config) in PROFILES.items():
            with self.subTest(kind=kind):
                text=(ROOT/f"penny-isolated-{kind}.service").read_text()
                lines=set(text.splitlines())
                for expected in (f"User={user}",f"Group={user}",
                    "Type=oneshot","WorkingDirectory=/opt/penny/release",
                    "NoNewPrivileges=yes","CapabilityBoundingSet=",
                    "AmbientCapabilities=","ProtectSystem=strict",
                    "ProtectHome=yes","PrivateTmp=yes","PrivateDevices=yes",
                    "RestrictNamespaces=yes","RestrictAddressFamilies=AF_UNIX AF_INET",
                    "SocketBindDeny=any","LimitCORE=0","UMask=0077"):
                    self.assertIn(expected,lines)
                self.assertIn(f"--config /etc/penny-private/{config}/{config}.json",text)
                self.assertIn("InaccessiblePaths=-/etc/penny-private/operator",text)
                for _,other in PROFILES.values():
                    if other!=config:
                        self.assertIn(f"-/etc/penny-private/{other}",text)
                self.assertNotIn("ReadWritePaths=",text)
                self.assertNotIn("Restart=always",text)
                self.assertNotIn("%h/",text)
                self.assertNotIn("ExecStart=+",text)
                if kind=="inference":
                    self.assertIn("IPAddressDeny=any",lines)
                    self.assertIn("IPAddressAllow=127.0.0.0/8",lines)
                timer=(ROOT/f"penny-isolated-{kind}.timer").read_text()
                self.assertIn(f"Unit=penny-isolated-{kind}.service",timer)
