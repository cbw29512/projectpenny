"""One supervised invocation. No daemon, installation or privilege escalation."""
import argparse
import logging

from penny.brain.local import LocalBrain
from penny.bridge.transport import BridgeClient
from penny.bridge.worker import run_bridge_once
from .config import load_config
from .inference import inference_tick


def main():
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(name)s %(message)s")
    parser=argparse.ArgumentParser()
    parser.add_argument("kind",choices=("inference","bridge"))
    parser.add_argument("--config",required=True)
    args=parser.parse_args()
    try:
        config=load_config(args.config,args.kind)
        if args.kind=="inference":
            status=inference_tick(config.dsn,LocalBrain())
        else:
            status=run_bridge_once(config.dsn,BridgeClient(config.host,config.key)).status
        logging.info("Runtime cycle: %s",status)
        return 0 if status!="blocked" else 1
    except Exception as exc:
        logging.error("Runtime invocation failed (%s)",type(exc).__name__)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
