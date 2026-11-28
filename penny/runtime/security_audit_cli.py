"""Run on NucBox using trusted local access; no firewall or SSH changes."""
import argparse
import json
import logging
from .security_audit import audit_security
from .security_audit_state import DesktopScope


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user")
    parser.add_argument("--desktop-ip")
    parser.add_argument("--server-ip")
    parser.add_argument("--desktop-host")
    parser.add_argument("--ssh-port",type=int,default=22)
    parser.add_argument("--protected-port",type=int,action="append",default=[])
    args=parser.parse_args()
    try:
        values=(args.user,args.desktop_ip,args.server_ip,args.desktop_host)
        if any(values) and not all(values):
            raise ValueError("complete desktop scope required")
        scope=DesktopScope(*values,args.ssh_port) if all(values) else None
        if scope:
            scope.connection_spec()
        print(json.dumps(audit_security(scope,protected_ports=args.protected_port),indent=2,sort_keys=True))
        return 0
    except Exception as exc:
        logging.error("Security inspection refused (%s)",type(exc).__name__)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
