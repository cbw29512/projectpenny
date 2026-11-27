"""Print private preflight results; never activate Penny."""
import argparse
import json
import logging
from pathlib import Path
from .preflight import preflight

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=Path.home() / ".config/penny")
    args = parser.parse_args()
    try:
        result = preflight(args.config_dir)
        print(json.dumps(result, indent=2, sort_keys=True))
        # Diagnostic only: even a successful collection is not a release gate.
        return 0
    except Exception as exc:
        logging.error("Preflight failed (%s)", type(exc).__name__)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
