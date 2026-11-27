"""Private explicitly authorized activity publication; no timer installed."""
import argparse
import logging

from .config import load_config
from penny.progress.publisher import publish_once


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",required=True)
    parser.add_argument("--confirm",action="store_true")
    args=parser.parse_args()
    try:
        if not args.confirm:
            print("Refused; explicit confirmation required.")
            return 1
        outcome=publish_once(load_config(args.config,"projection"),confirmed=True)
        print(outcome)
        return 0 if outcome=="published" else 1
    except Exception as exc:
        logging.error("Activity publisher refused (%s)",type(exc).__name__)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
