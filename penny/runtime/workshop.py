"""Interim local SSH Workshop CLI; no public route or shell/model execution."""
import argparse
import json
import logging
import sys
from uuid import UUID

from penny.business.workshop_operator import recent,inspect
from penny.business.quality import review,export_private
from penny.business.quality_state import CRITERIA
from .config import load_config
from .private_evidence import read_evidence


def parser():
    p=argparse.ArgumentParser(description="Private Penny Workshop operator")
    p.add_argument("--config",required=True)
    commands=p.add_subparsers(dest="action",required=True)
    listing=commands.add_parser("list")
    listing.add_argument("--limit",type=int,default=20)
    show=commands.add_parser("inspect")
    show.add_argument("task_id",type=UUID)
    for name in ("review","revoke"):
        cmd=commands.add_parser(name)
        cmd.add_argument("task_id",type=UUID)
        cmd.add_argument("--digest",required=True)
        cmd.add_argument("--source-ref",required=True)
        cmd.add_argument("--reviewer-id",required=True,type=UUID)
        cmd.add_argument("--evidence-ref",required=True)
        cmd.add_argument("--evidence-file",required=True)
        cmd.add_argument("--confirm",action="store_true")
        if name=="review":
            for criterion in CRITERIA:
                cmd.add_argument("--"+criterion,choices=("pass","fail"),required=True)
    export=commands.add_parser("export")
    export.add_argument("task_id",type=UUID)
    export.add_argument("--review-id",required=True,type=UUID)
    export.add_argument("--digest",required=True)
    return p


def main(argv=None):
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(name)s %(message)s")
    args=parser().parse_args(argv)
    try:
        dsn=load_config(args.config,"operator").dsn
        if args.action=="list":
            result=recent(dsn,limit=args.limit)
        elif args.action=="inspect":
            result=inspect(dsn,args.task_id)
        elif args.action in ("review","revoke"):
            if not args.confirm:
                raise ValueError("explicit review confirmation required")
            revoked=args.action=="revoke"
            checks={k:False if revoked else getattr(args,k)=="pass" for k in CRITERIA}
            receipt=review(dsn,args.task_id,source_ref=args.source_ref,
                expected_content_sha256=args.digest,checks=checks,revoked=revoked,
                reviewer_id=args.reviewer_id,evidence_ref=args.evidence_ref,
                evidence=read_evidence(args.evidence_file),confirmed=True)
            result=None if receipt is None else {"review_id":str(receipt.entry_id),
                                                 "replayed":receipt.replayed}
        else:
            # Export is binary stdout only. Refuse a terminal, since model text
            # is untrusted; shell redirection is a separate operator action.
            if sys.stdout.isatty():
                raise ValueError("redirect private export to a protected file")
            product=export_private(dsn,args.task_id,expected_review_id=args.review_id,
                                   expected_content_sha256=args.digest)
            if product is None:
                raise PermissionError("export refused")
            sys.stdout.buffer.write(product.content)
            sys.stdout.buffer.flush()
            return 0
        if result is None:
            raise PermissionError("operator action refused")
        # ASCII-escaped JSON prevents raw control characters from reaching a terminal.
        print(json.dumps(result,ensure_ascii=True,indent=2,sort_keys=True))
        return 0
    except Exception as exc:
        logging.error("Workshop command failed (%s)",type(exc).__name__)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
