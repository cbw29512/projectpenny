"""No network or sleep: synthetic rehearsal transport."""
import unittest
from unittest.mock import Mock
from penny.runtime.workshop_smoke import verify

HOST="a"*24+"--projectpenny.netlify.app"


class SmokeTests(unittest.TestCase):
    def test_production_or_unconfirmed_refused(self):
        send=Mock()
        for host,confirmed in (("projectpenny.netlify.app",True),(HOST,False)):
            self.assertEqual(verify(host,confirmed=confirmed,send=send)["status"],"refused")
        send.assert_not_called()

    def test_bounded_delayed_enforcement(self):
        send=Mock(side_effect=["smoke"]*7+["limited"]+["smoke"]*4+["limited"])
        delay=Mock()
        result=verify(HOST,confirmed=True,send=send,delay=delay,clock=lambda:0)
        self.assertEqual(result["status"],"observed")
        self.assertEqual(result["requests"],13)
        self.assertEqual(send.call_count,13)
        self.assertEqual(delay.call_count,2)

    def test_early_429_or_wrong_response_inconclusive(self):
        for response in ("limited","unexpected"):
            send=Mock(return_value=response)
            self.assertEqual(verify(HOST,confirmed=True,send=send)["status"],"inconclusive")
            send.assert_called_once()

    def test_no_429_stops_before_second_route(self):
        send=Mock(return_value="smoke")
        self.assertEqual(verify(HOST,confirmed=True,send=send,delay=Mock(),clock=lambda:0),
                         {"status":"inconclusive","requests":8})
