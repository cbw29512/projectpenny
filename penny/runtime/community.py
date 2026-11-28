"""Private Maker suggestion review commands; no public interface."""
import argparse
import json
import logging
from uuid import UUID

from penny.community.suggestion_queue import pending_suggestions
from penny.community.review import review_suggestion
from penny.community.suggestion_state import Verdict, REASONS
from .config import load_config

logger = logging.getLogger(__name__)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    commands = parser.add_subparsers(dest="action", required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--limit", type=int, default=20)
    review = commands.add_parser("review")
    review.add_argument("suggestion_id", type=UUID)
    review.add_argument("--digest", required=True)
    review.add_argument("--verdict", choices=[v.value for v in Verdict], required=True)
    review.add_argument("--reason", required=True)
    review.add_argument("--reviewer-id", type=UUID, required=True)
    review.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "review":
            verdict = Verdict(args.verdict)
            if not args.confirm or args.reason not in REASONS[verdict]:
                raise ValueError("explicit confirmed decision required")
        dsn = load_config(args.config, "operator").dsn
        if args.action == "list":
            result = pending_suggestions(dsn, limit=args.limit)
        else:
            if not review_suggestion(dsn, args.suggestion_id,
                    expected_sha256=args.digest, verdict=verdict, reason=args.reason,
                    reviewer_id=args.reviewer_id):
                raise PermissionError("suggestion review refused")
            result = {"status": "reviewed", "suggestion_id": str(args.suggestion_id)}
        # Untrusted text is JSON-escaped, not executed or printed as raw controls.
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    except Exception as exc:
        logger.error("Suggestion operator action refused (%s)", type(exc).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
