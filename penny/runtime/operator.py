"""Private SSH operator CLI. No web routes, model tools or stored secrets in argv."""
import argparse
import json
import logging
from uuid import UUID

from .config import load_config
from .operator_status import status
from .operator_control import stop,start,recover_inference,clear_bridge_block
from penny.progress.rest import configure
from penny.progress.activity import browser_candidate as activity_candidate
from penny.progress.rest import browser_candidate as rest_candidate


def main():
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(name)s %(message)s")
    parser=argparse.ArgumentParser(description="Trusted local Penny operator")
    parser.add_argument("--config",required=True)
    commands=parser.add_subparsers(dest="action",required=True)
    commands.add_parser("status")
    commands.add_parser("activity-candidate")
    commands.add_parser("rest-candidate")
    commands.add_parser("stop")
    enable=commands.add_parser("start")
    enable.add_argument("kind",choices=("inference","bridge"))
    enable.add_argument("--confirm",action="store_true")
    recover=commands.add_parser("recover-inference")
    recover.add_argument("--confirmed-isolated",action="store_true")
    recover.add_argument("--task-id",type=UUID)
    recover.add_argument("--fence",type=UUID)
    clear=commands.add_parser("clear-bridge-block")
    clear.add_argument("--confirmed-reviewed",action="store_true")
    rest=commands.add_parser("rest-policy")
    rest.add_argument("mode",choices=("enable","disable"))
    rest.add_argument("--confirm",action="store_true")
    args=parser.parse_args()
    try:
        dsn=load_config(args.config,"operator").dsn
        if args.action=="status":
            print(json.dumps(status(dsn),indent=2,sort_keys=True))
            return 0
        if args.action in ("activity-candidate","rest-candidate"):
            candidate=activity_candidate if args.action=="activity-candidate" else rest_candidate
            print(json.dumps(candidate(dsn),sort_keys=True))
            return 0
        if args.action=="stop":
            ok=stop(dsn)
        elif args.action=="start":
            ok=start(dsn,args.kind,confirmed=args.confirm)
        elif args.action=="recover-inference":
            ok=recover_inference(dsn,isolated=args.confirmed_isolated,
                                 task_id=args.task_id,fence=args.fence)
        elif args.action=="rest-policy":
            ok=configure(dsn,args.mode=="enable",confirmed=args.confirm)
        else:
            ok=clear_bridge_block(dsn,reviewed=args.confirmed_reviewed)
        print("Recorded." if ok else "Refused; inspect private runtime status.")
        return 0 if ok else 1
    except Exception as exc:
        logging.error("Operator command failed (%s)",type(exc).__name__)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
