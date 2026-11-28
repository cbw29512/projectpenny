"""Beta operator CLI boundaries; synthetic bytes and mocked services only."""
import contextlib
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from penny.business.beta_proof import BetaProof
from penny.runtime.beta import main


class BetaCliTests(unittest.TestCase):
    def setUp(self):
        self.grant,self.preview,self.review,self.member,self.reviewer=(uuid4() for _ in range(5))
        self.proof=BetaProof("a"*64,"b"*64,b"synthetic private beta bytes")
        self.base=["--config","private.json"]
        self.common=[str(self.grant),"--preview-id",str(self.preview),
                     "--review-id",str(self.review),"--version","v1","--artwork","private.png"]
        self.hashes=["--edition-sha256",self.proof.edition_sha256,
                     "--variant-sha256",self.proof.variant_sha256]
        self.evidence=["--reviewer-id",str(self.reviewer),"--evidence-ref","test:review",
                       "--evidence-file","private.txt"]

    def invoke(self,args,out):
        with patch("penny.runtime.beta.load_config",return_value=SimpleNamespace(dsn="fixture")), \
             patch("penny.runtime.beta.read_private_file",return_value=b"artwork"), \
             contextlib.redirect_stdout(out):
            return main(self.base+args)

    @patch("penny.runtime.beta.prepare_beta")
    def test_inspect_has_digests_not_content_or_authority(self,prepare):
        prepare.return_value=self.proof
        out=io.StringIO()
        self.assertEqual(self.invoke(["inspect",*self.common],out),0)
        result=json.loads(out.getvalue())
        self.assertEqual(result["variant_sha256"],self.proof.variant_sha256)
        self.assertFalse(result["access_granted"])
        self.assertFalse(result["commercial_release_authorized"])
        self.assertNotIn("content",result)
        self.assertNotIn("fixture",out.getvalue())

    @patch("penny.runtime.beta.prepare_beta")
    def test_export_confirmation_and_exact_digest(self,prepare):
        prepare.return_value=self.proof
        for args,expected in ((self.hashes,1),
            (["--edition-sha256","0"*64,"--variant-sha256","b"*64,"--confirm"],1),
            (self.hashes+["--confirm"],0)):
            stream=io.BytesIO()
            out=io.TextIOWrapper(stream,encoding="utf-8")
            self.assertEqual(self.invoke(["export",*self.common,*args],out),expected)
            self.assertEqual(stream.getvalue(),self.proof.content if expected==0 else b"")

    @patch("penny.runtime.beta.grant_beta",return_value=True)
    @patch("penny.runtime.beta.read_evidence",return_value=b"synthetic review")
    def test_grant_requires_confirmation_and_exact_arguments(self,read,grant):
        args=["grant",*self.common,*self.hashes,*self.evidence,
              "--member-id",str(self.member),"--expires-at","2000000000"]
        self.assertEqual(self.invoke(args,io.StringIO()),1)
        read.assert_not_called()
        grant.assert_not_called()
        self.assertEqual(self.invoke(args+["--confirm"],io.StringIO()),0)
        kwargs=grant.call_args.kwargs
        self.assertEqual(kwargs["member_id"],self.member)
        self.assertEqual(kwargs["variant_sha256"],self.proof.variant_sha256)
        self.assertEqual(kwargs["expires_at"],2000000000)
        self.assertTrue(kwargs["confirmed"])
        self.assertEqual(grant.call_args.args,("fixture",self.grant))

    @patch("penny.runtime.beta.revoke_beta",return_value=True)
    @patch("penny.runtime.beta.read_evidence",return_value=b"synthetic review")
    def test_revoke_no_artwork_or_proof(self,read,revoke):
        args=["revoke",str(self.grant),*self.evidence]
        self.assertEqual(self.invoke(args,io.StringIO()),1)
        revoke.assert_not_called()
        self.assertEqual(self.invoke(args+["--confirm"],io.StringIO()),0)
        self.assertEqual(revoke.call_args.args,("fixture",self.grant))
