"""Trusted activity delivery control and one bounded cycle."""
import argparse
import logging

from .config import load_config
from penny.progress.publisher import publish_once
from penny.progress.delivery_gate import configure,clear_interrupted


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",required=True)
    parser.add_argument("--confirm",action="store_true")
    parser.add_argument("--mode",choices=("once","cycle","enable","disable","recover"),default="once")
    parser.add_argument("--daily-limit",type=int,default=0)
    args=parser.parse_args()
    try:
        if args.mode!="cycle" and not args.confirm:
            print("Refused; explicit confirmation required.")
            return 1
        config=load_config(args.config,"projection")
        if args.mode in ("enable","disable"):
            ok=configure(config,enabled=args.mode=="enable",limit=args.daily_limit,confirmed=args.confirm)
            print("Recorded." if ok else "Refused.")
            return 0 if ok else 1
        if args.mode=="recover":
            return 0 if clear_interrupted(config.dsn,confirmed=args.confirm) else 1
        outcome=publish_once(config,confirmed=True)
        print(outcome)
        return 0 if outcome in ("published","paused","cooldown","budget_exhausted","busy") else 1
    except Exception as exc:
        logging.error("Activity publisher refused (%s)",type(exc).__name__)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
