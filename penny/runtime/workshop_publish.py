"""Trusted local Workshop publication controls. No public admin route."""
import argparse
import logging

from penny.progress.workshop_gate import configure
from penny.progress.workshop_publisher import publish_once
from .config import load_config


def main(argv=None):
    logging.basicConfig(level=logging.INFO)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",required=True)
    commands=p.add_subparsers(dest="action",required=True)
    for action in ("enable","disable","reconcile","publish-once"):
        cmd=commands.add_parser(action)
        cmd.add_argument("--confirm",action="store_true")
        if action=="enable":
            cmd.add_argument("--daily-limit",type=int,required=True)
    a=p.parse_args(argv)
    try:
        if not a.confirm:
            raise PermissionError("explicit confirmation required")
        config=load_config(a.config,"workshop")
        if a.action=="publish-once":
            result=publish_once(config,confirmed=True)
            print(result)
            return 0 if result=="published" else 1
        ok=configure(config,enabled=a.action=="enable",
                     limit=a.daily_limit if a.action=="enable" else 0,
                     reconciled=a.action=="reconcile",confirmed=True)
        print("configured" if ok else "refused")
        return 0 if ok else 1
    except Exception as exc:
        logging.error("Workshop publication command refused (%s)",type(exc).__name__)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
