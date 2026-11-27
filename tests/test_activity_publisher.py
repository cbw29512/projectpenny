"""No real network, credentials or inference."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from penny.progress.publisher import _send_once as publish_once, signature, PATH


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.config=SimpleNamespace(host="penny-test.netlify.app",dsn="private",
                                    key=b"\x07"*32)
        self.sample={"schema":"penny-activity-v1","status":"reviewed","state":"working",
                     "sampled_at":999,"expires_at":1014}

    @patch("penny.progress.publisher.http.client.HTTPSConnection")
    @patch("penny.progress.publisher.time.time",return_value=1000)
    @patch("penny.progress.publisher.browser_candidate")
    def test_exact_public_wire_and_no_unconfirmed_request(self,candidate,clock,https):
        candidate.return_value=self.sample
        self.assertEqual(publish_once(self.config),"refused")
        https.assert_not_called()
        conn=https.return_value
        response=conn.getresponse.return_value
        response.status=200
        response.getheader.side_effect=lambda key,default=None: (
            "application/json" if key=="Content-Type" else default)
        response.read.return_value=b'{"status":"ok"}'
        self.assertEqual(publish_once(self.config,confirmed=True),"published")
        args=conn.request.call_args
        self.assertEqual(args.args,("POST",PATH))
        self.assertEqual(json.loads(args.kwargs["body"]),{"sampled_at":999,"activity":"working"})
        self.assertEqual(args.kwargs["headers"]["Authorization"],
                         "PennyActivity v1."+signature(self.config.key,999,"working"))
        candidate.return_value={**self.sample,"prompt":"private"}
        self.assertEqual(publish_once(self.config,confirmed=True),"unavailable")
        self.assertEqual(conn.request.call_count,1)
        candidate.return_value={**self.sample,"sampled_at":980,"expires_at":995}
        self.assertEqual(publish_once(self.config,confirmed=True),"unavailable")
        self.assertEqual(conn.request.call_count,1)
