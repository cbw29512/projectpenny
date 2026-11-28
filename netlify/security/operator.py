"""Maker-only cloud database tools. No provisioning, upgrades, or activation."""
import argparse
import json
import logging

import psycopg
from psycopg import sql
from .manifest import release_plan
from .install import install_fresh
from .login import probe_login
from .operator_config import load

logger=logging.getLogger(__name__)


def apply(config,digest):
    # Never accept an owner or privileged role from a browser or a request.
    with psycopg.connect(config.dsn,autocommit=True,connect_timeout=5) as conn:
        row=conn.execute("""SELECT current_database(),current_user,session_user,
            COALESCE((SELECT ssl FROM pg_catalog.pg_stat_ssl
                      WHERE pid=pg_backend_pid()),false)""").fetchone()
        if row!=(config.database,config.login,config.login,True):
            raise PermissionError("unexpected installation connection")
        conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(config.owner)))
        return install_fresh(conn,database=config.database,schema="penny_mailbox",
            roles=config.roles,expected_digest=digest,confirmed=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="action",required=True)
    sub.add_parser("plan")
    install=sub.add_parser("install")
    install.add_argument("--config",required=True)
    install.add_argument("--release-sha256",required=True)
    install.add_argument("--confirm",action="store_true")
    probe=sub.add_parser("probe")
    probe.add_argument("--config",required=True)
    args=parser.parse_args(argv)
    try:
        if args.action=="plan":
            digest,entries=release_plan()
            result={"release_sha256":digest,"migrations":[
                {"name":name,"sha256":sha} for name,sha,_ in entries]}
        elif args.action=="install":
            # Refuse before reading credentials or opening a connection.
            if not args.confirm or args.release_sha256!=release_plan()[0]:
                raise PermissionError("reviewed release confirmation required")
            config=load(args.config,"install")
            result=apply(config,args.release_sha256)
        else:
            config=load(args.config,"probe")
            report=probe_login(config.dsn,database=config.database,role=config.login,
                               scope=config.scope)
            result={"scope":config.scope,"checks_passed":report.ready,
                    "issues":report.issues,"production_certified":False}
            print(json.dumps(result,sort_keys=True))
            return 0 if report.ready else 1
        print(json.dumps(result,sort_keys=True))
        return 0
    except Exception as exc:
        logger.error("Cloud operator action refused (%s)",type(exc).__name__)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
