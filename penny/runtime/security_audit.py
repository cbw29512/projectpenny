"""Read-only SSH and TCP listener inspection; never invokes sudo or changes policy."""
import logging
import subprocess

from .security_audit_state import DesktopScope,ssh_findings,listener_findings

logger=logging.getLogger(__name__)
MAX_OUTPUT=262144
# Defaults from dedicated local PostgreSQL and Ollama contracts. Extra ports
# must be supplied by the operator; no claim of discovering every Penny service.
DEFAULT_PORTS=(5432,11434)


def collect(argv):
    result=subprocess.run(argv,capture_output=True,text=True,encoding="utf-8",
                          errors="strict",timeout=5,check=False,
                          env={"PATH":"/usr/sbin:/usr/bin:/sbin:/bin","LC_ALL":"C"})
    if result.returncode!=0 or len(result.stdout)>MAX_OUTPUT:
        raise RuntimeError("inspection unavailable")
    return result.stdout


def audit_security(scope=None,*,protected_ports=DEFAULT_PORTS):
    if scope is not None and type(scope) is not DesktopScope:
        raise ValueError("invalid desktop scope")
    if (not isinstance(protected_ports,(tuple,list)) or len(protected_ports)>32
            or any(type(p) is not int or not 1<=p<=65535 for p in protected_ports)):
        raise ValueError("invalid protected ports")
    findings={"schema":"penny-local-security-audit-v1","certified":False,
              "firewall":"not_verified","router_exposure":"not_verified",
              "desktop_source_restriction":"not_verified","host_key":"not_verified",
              "running_sshd_config":"not_verified"}
    try:
        rows=listener_findings(collect(["/usr/bin/ss","-H","-lnt"]),
                               set(DEFAULT_PORTS)|set(protected_ports),scope.port if scope else 22)
        findings["listeners"]={"status":"collected","rows":rows,
            "protected_nonloopback":any(r["category"]=="protected_port" and r["binding"]!="loopback" for r in rows)}
    except Exception as exc:
        logger.warning("Listener audit unavailable (%s)",type(exc).__name__)
        findings["listeners"]={"status":"unavailable"}
    if scope is None:
        findings["ssh"]={"status":"desktop_scope_required"}
    else:
        try:
            spec=scope.connection_spec()
            raw=collect(["/usr/sbin/sshd","-T","-C",spec])
            fields=ssh_findings(raw)
            findings["ssh"]={"status":"candidate_policy_matches" if all(v=="matches" for v in fields.values())
                             else "review_required","checks":fields}
        except Exception as exc:
            logger.warning("SSH policy audit unavailable (%s)",type(exc).__name__)
            findings["ssh"]={"status":"unavailable"}
    return findings
