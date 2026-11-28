"""Mocked community cycle; no remote network."""
import unittest
from unittest.mock import Mock,patch
from contextlib import nullcontext
from uuid import uuid4
from penny.bridge.state import BridgeResult
from penny.community.transport_state import CommunityClaim
from penny.community.worker import run_community_once


class CommunityWorkerTests(unittest.TestCase):
    def setUp(self):
        self.claim=CommunityClaim(uuid4(),uuid4(),uuid4(),uuid4(),2000,1500,"Useful idea")
        self.client=Mock()
        self.client.community_claim.return_value=BridgeResult("claimed",self.claim)
        self.client.community_ack.return_value=BridgeResult("ok")

    @patch("penny.community.worker.identity_matches",return_value=True)
    @patch("penny.community.worker.exclusive_cycle",return_value=nullcontext(True))
    @patch("penny.community.worker.reply_call")
    @patch("penny.community.worker.persist_claim")
    def test_ack_only_after_storage_and_verification(self,persist,db,lock,identity):
        persist.return_value=True
        db.side_effect=[{"recorded":True},{"recorded":True},{"recorded":True}]
        self.assertEqual(run_community_once("fixture",self.client).status,"acknowledged")
        self.client.community_ack.assert_called_once_with(self.claim.id,self.claim.fence)
        self.assertEqual([c.args[1] for c in db.call_args_list],["community_reserve","community_verify","community_record_ack"])

    @patch("penny.community.worker.identity_matches",return_value=True)
    @patch("penny.community.worker.exclusive_cycle",return_value=nullcontext(True))
    @patch("penny.community.worker.reply_call",return_value={"recorded":True})
    @patch("penny.community.worker.persist_claim",return_value=False)
    def test_failed_admission_never_acknowledges(self,persist,db,lock,identity):
        self.assertEqual(run_community_once("fixture",self.client).status,"not_admitted")
        self.client.community_ack.assert_not_called()

    @patch("penny.community.worker.identity_matches",return_value=True)
    @patch("penny.community.worker.exclusive_cycle",return_value=nullcontext(True))
    @patch("penny.community.worker.reply_call",return_value={"recorded":False})
    def test_closed_gate_never_contacts_network(self,db,lock,identity):
        self.assertEqual(run_community_once("fixture",self.client).status,"paused")
        self.client.community_claim.assert_not_called()

    @patch("penny.community.worker.identity_matches",return_value=True)
    @patch("penny.community.worker.exclusive_cycle",return_value=nullcontext(True))
    @patch("penny.community.worker.reply_call")
    @patch("penny.community.worker.persist_claim",return_value=True)
    def test_remote_success_without_local_evidence_is_not_complete(self,persist,db,lock,identity):
        db.side_effect=[{"recorded":True},{"recorded":True},{"recorded":False}]
        self.assertEqual(run_community_once("fixture",self.client).status,"ack_unrecorded")
        self.client.community_ack.assert_called_once()
