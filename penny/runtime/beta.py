"""Trusted local beta operator; never a public download or member API."""
import argparse
import json
import logging
import sys
from uuid import UUID

from penny.business.beta_proof import prepare_beta
from penny.business.beta_grants import grant_beta,revoke_beta
from penny.business.brand import MAX_ARTWORK_BYTES
from .config import load_config
from .private_evidence import read_private_file,read_evidence


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",required=True)
    commands=p.add_subparsers(dest="action",required=True)
    for name in ("inspect","export","grant","revoke"):
        cmd=commands.add_parser(name)
        cmd.add_argument("grant_id",type=UUID)
        if name!="revoke":
            cmd.add_argument("--preview-id",type=UUID,required=True)
            cmd.add_argument("--review-id",type=UUID,required=True)
            cmd.add_argument("--version",required=True)
            cmd.add_argument("--artwork",required=True)
        if name in ("export","grant"):
            cmd.add_argument("--edition-sha256",required=True)
            cmd.add_argument("--variant-sha256",required=True)
        if name in ("grant","revoke"):
            cmd.add_argument("--reviewer-id",type=UUID,required=True)
            cmd.add_argument("--evidence-ref",required=True)
            cmd.add_argument("--evidence-file",required=True)
        if name=="grant":
            cmd.add_argument("--member-id",type=UUID,required=True)
            cmd.add_argument("--expires-at",type=int,required=True)
        if name!="inspect":
            cmd.add_argument("--confirm",action="store_true")
    return p


def main(argv=None):
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(name)s %(message)s")
    a=parser().parse_args(argv)
    try:
        if a.action!="inspect" and not a.confirm:
            raise PermissionError("explicit confirmation required")
        if a.action=="export" and sys.stdout.isatty():
            raise PermissionError("redirect private proof to protected file")
        dsn=load_config(a.config,"operator").dsn
        if a.action=="revoke":
            ok=revoke_beta(dsn,a.grant_id,reviewer_id=a.reviewer_id,
                evidence_ref=a.evidence_ref,evidence=read_evidence(a.evidence_file),confirmed=True)
            return 0 if ok else 1
        artwork=read_private_file(a.artwork,MAX_ARTWORK_BYTES)
        if a.action=="grant":
            # Grant function independently reconstructs and checks exact bytes
            # under its own lock; never authorize using an earlier CLI result.
            ok=grant_beta(dsn,a.grant_id,preview_id=a.preview_id,member_id=a.member_id,
                quality_review_id=a.review_id,brand_version=a.version,
                edition_sha256=a.edition_sha256,variant_sha256=a.variant_sha256,
                artwork=artwork,reviewer_id=a.reviewer_id,evidence_ref=a.evidence_ref,
                evidence=read_evidence(a.evidence_file),expires_at=a.expires_at,confirmed=True)
            return 0 if ok else 1
        proof=prepare_beta(dsn,a.preview_id,a.grant_id,quality_review_id=a.review_id,
                           brand_version=a.version,artwork=artwork)
        if proof is None:
            raise PermissionError("beta proof unavailable")
        if a.action=="inspect":
            print(json.dumps({"grant_id":str(a.grant_id),"preview_id":str(a.preview_id),
                "edition_sha256":proof.edition_sha256,"variant_sha256":proof.variant_sha256,
                "access_granted":False,"commercial_release_authorized":False},
                sort_keys=True,indent=2))
        else:
            if (proof.edition_sha256,proof.variant_sha256)!=(a.edition_sha256,a.variant_sha256):
                raise PermissionError("beta proof digest mismatch")
            sys.stdout.buffer.write(proof.content)
            sys.stdout.buffer.flush()
        return 0
    except Exception as exc:
        logging.error("Beta operator command refused (%s)",type(exc).__name__)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
