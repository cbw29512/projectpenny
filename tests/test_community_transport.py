"""Pure contract and mocked scoped database adapter tests."""
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
from penny.community.transport_state import parse_community_claim
from penny.community.scoped import persist_claim


class CommunityTransportTests(unittest.TestCase):
    def setUp(self):
        self.now = int(time.time())
        self.wire = dict(id=str(uuid4()),owner=str(uuid4()),key=str(uuid4()),
                         fence=str(uuid4()),text="Make a calendar",
                         expiresAt=self.now+600,leaseUntil=self.now+300)

    def test_claim_contract(self):
        claim = parse_community_claim(self.wire,self.now)
        self.assertNotIn(self.wire["text"],repr(claim))
        for change in (dict(role="admin"),dict(leaseUntil=self.now),
                       dict(leaseUntil=self.now+901),dict(expiresAt=self.now+3601),
                       dict(leaseUntil=True),dict(text="Café idea"),
                       dict(text="idea\u200b"),dict(owner="admin")):
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse_community_claim(self.wire | change,self.now)

    @patch("penny.community.scoped.reply_call")
    def test_persistence_requires_committed_success(self,db):
        claim = parse_community_claim(self.wire,self.now)
        db.return_value={"recorded":True}
        self.assertTrue(persist_claim("fixture",claim))
        db.assert_called_once_with("fixture","community_admit",
            (claim.id,claim.owner,claim.key,claim.fence,claim.text,
             claim.expires_at,claim.lease_until))
        db.return_value={"recorded":False}
        self.assertFalse(persist_claim("fixture",claim))
        db.side_effect=RuntimeError("synthetic transaction failure")
        self.assertFalse(persist_claim("fixture",claim))

    @patch("penny.community.scoped.authorize")
    @patch("penny.community.scoped.reply_call")
    def test_guardian_denial_never_calls_database(self,db,authorize):
        authorize.return_value.allowed=False
        self.assertFalse(persist_claim("fixture",parse_community_claim(self.wire,self.now)))
        db.assert_not_called()
