"""Private operator brand approval and printable proof. No public release."""
import argparse
import json
import logging
import sys
from uuid import UUID

from penny.business.brand import approve,revoke,MAX_ARTWORK_BYTES
from penny.business.edition import build_private
from penny.business.printable import png_envelope
from .config import load_config
from .private_evidence import read_private_file,read_evidence


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",required=True)
    commands=p.add_subparsers(dest="action",required=True)
    for name in ("approve","revoke"):
        cmd=commands.add_parser(name)
        cmd.add_argument("version")
        cmd.add_argument("--reviewer-id",required=True,type=UUID)
        cmd.add_argument("--evidence-file",required=True)
        cmd.add_argument("--confirm",action="store_true")
        if name=="approve":
            cmd.add_argument("--artwork",required=True)
            cmd.add_argument("--artwork-sha256",required=True)
            cmd.add_argument("--rights-ref",required=True)
        else:
            cmd.add_argument("--evidence-ref",required=True)
    for name in ("inspect","export"):
        cmd=commands.add_parser(name)
        cmd.add_argument("task_id",type=UUID)
        cmd.add_argument("--review-id",required=True,type=UUID)
        cmd.add_argument("--digest",required=True)
        cmd.add_argument("--version",required=True)
        cmd.add_argument("--artwork",required=True)
        if name=="export":
            cmd.add_argument("--edition-sha256",required=True)
            cmd.add_argument("--confirm",action="store_true")
    return p


def main(argv=None):
    logging.basicConfig(level=logging.INFO)
    a=parser().parse_args(argv)
    try:
        dsn=load_config(a.config,"operator").dsn
        if a.action in ("approve","revoke","export") and not a.confirm:
            raise PermissionError("explicit confirmation required")
        if a.action=="approve":
            artwork=read_private_file(a.artwork,MAX_ARTWORK_BYTES)
            if not png_envelope(artwork):
                raise ValueError("invalid PNG envelope")
            ok=approve(dsn,a.version,artwork=artwork,expected_sha256=a.artwork_sha256,
                       reviewer_id=a.reviewer_id,rights_ref=a.rights_ref,
                       evidence=read_evidence(a.evidence_file),confirmed=True)
            return 0 if ok else 1
        if a.action=="revoke":
            ok=revoke(dsn,a.version,reviewer_id=a.reviewer_id,evidence_ref=a.evidence_ref,
                      evidence=read_evidence(a.evidence_file),confirmed=True)
            return 0 if ok else 1
        edition=build_private(dsn,a.task_id,review_id=a.review_id,source_sha256=a.digest,
                              brand_version=a.version,artwork=read_private_file(a.artwork,MAX_ARTWORK_BYTES))
        if edition is None:
            raise PermissionError("edition refused")
        if a.action=="inspect":
            print(json.dumps(edition.manifest(),sort_keys=True,indent=2))
        else:
            if sys.stdout.isatty() or edition.edition_sha256!=a.edition_sha256:
                raise PermissionError("redirect exact private proof to protected file")
            sys.stdout.buffer.write(edition.content)
            sys.stdout.buffer.flush()
        return 0
    except Exception as exc:
        logging.error("Brand operator refused (%s)",type(exc).__name__)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
