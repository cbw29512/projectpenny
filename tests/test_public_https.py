"""Public-only outbound connector; all sockets and DNS synthetic."""
import socket
import ssl
import unittest
from unittest.mock import Mock,patch

from penny.bridge.public_https import public_ipv4,resolve_public,PublicHTTPSConnection
HOST="fixture.netlify.app"

def answer(ip):
    return (socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,"",(ip,443))


class PublicHTTPSTests(unittest.TestCase):
    def test_special_addresses_rejected(self):
        for ip in ("127.0.0.1","10.1.2.3","172.16.1.1","192.168.1.1",
                   "169.254.169.254","100.64.1.1","0.0.0.0","224.1.1.1",
                   "240.0.0.1","192.0.0.9","198.18.1.1","192.0.2.1",
                   "::1","::ffff:127.0.0.1","64:ff9b::a00:1","invalid"):
            with self.subTest(ip=ip):
                self.assertFalse(public_ipv4(ip))
        self.assertTrue(public_ipv4("8.8.8.8"))

    @patch("penny.bridge.public_https.socket.getaddrinfo")
    @patch("penny.bridge.public_https.socket.socket")
    def test_mixed_resolution_never_connects(self,sock,dns):
        dns.return_value=[answer("8.8.8.8"),answer("127.0.0.1")]
        # Create context before patching SSL internals would be needed for a
        # full TLS handshake; here only validated context attributes matter.
        context=Mock(check_hostname=True,verify_mode=ssl.CERT_REQUIRED)
        connection=PublicHTTPSConnection(HOST,context=context)
        with self.assertRaises(PermissionError):
            connection.connect()
        sock.assert_not_called()

    @patch("penny.bridge.public_https.socket.getaddrinfo")
    @patch("penny.bridge.public_https.socket.socket")
    def test_single_numeric_connection_preserves_tls_hostname(self,sock,dns):
        dns.return_value=[answer("8.8.8.8")]
        raw=sock.return_value
        raw.getpeername.return_value=("8.8.8.8",443)
        context=Mock(check_hostname=True,verify_mode=ssl.CERT_REQUIRED)
        connection=PublicHTTPSConnection(HOST,context=context)
        connection.connect()
        dns.assert_called_once_with(HOST,443,socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP)
        raw.connect.assert_called_once_with(("8.8.8.8",443))
        context.wrap_socket.assert_called_once_with(raw,server_hostname=HOST)
        self.assertIs(connection.sock,context.wrap_socket.return_value)
        with self.assertRaises(PermissionError):
            connection.set_tunnel("localhost")

    def test_unapproved_host_and_insecure_tls_rejected(self):
        with self.assertRaises(ValueError):
            resolve_public("localhost")
        with self.assertRaises(ValueError):
            PublicHTTPSConnection(HOST,context=ssl._create_unverified_context())

    @patch("penny.bridge.public_https.socket.getaddrinfo")
    @patch("penny.bridge.public_https.socket.socket")
    def test_peer_mismatch_closes_socket_before_tls(self,sock,dns):
        dns.return_value=[answer("8.8.8.8")]
        sock.return_value.getpeername.return_value=("10.0.0.1",443)
        context=Mock(check_hostname=True,verify_mode=ssl.CERT_REQUIRED)
        with self.assertRaises(PermissionError):
            PublicHTTPSConnection(HOST,context=context).connect()
        sock.return_value.close.assert_called_once()
        context.wrap_socket.assert_not_called()
