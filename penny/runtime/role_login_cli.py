"""Private per-service readiness probe. Run as that service's OS account."""
import argparse
import json
import logging

from .config import load_config
from .role_state import SCOPES,valid_name,valid_schema
from .role_login import probe_login


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",required=True)
    parser.add_argument("--scope",choices=tuple(SCOPES),required=True)
    parser.add_argument("--schema",required=True)
    parser.add_argument("--role",required=True)
    args=parser.parse_args(argv)
    try:
        if not valid_schema(args.schema) or not valid_name(args.role):
            raise ValueError("invalid audit target")
        config=load_config(args.config,args.scope)
        report=probe_login(config.dsn,args.schema,args.role,args.scope)
        # No DSN, credential, raw database error, task text or account path.
        print(json.dumps({"scope":args.scope,"checks_passed":report.ready,
                          "issues":report.issues,"production_certified":False}))
        return 0 if report.ready else 1
    except Exception as exc:
        logging.error("Private login probe failed (%s)",type(exc).__name__)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
