"""Narrow public IPv4 HTTPS connection; no private network or DNS re-resolution."""
import http.client
import ipaddress
import logging
import re
import socket
import ssl

logger = logging.getLogger(__name__)
HOST = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.netlify\.app\Z")
# Conservative exclusions independent of Python's special-use registry version.
SPECIAL = tuple(ipaddress.IPv4Network(n) for n in (
    "0.0.0.0/8","10.0.0.0/8","100.64.0.0/10","127.0.0.0/8",
    "169.254.0.0/16","172.16.0.0/12","192.0.0.0/24","192.0.2.0/24",
    "192.88.99.0/24","192.168.0.0/16","198.18.0.0/15",
    "198.51.100.0/24","203.0.113.0/24","224.0.0.0/3",
))


def public_ipv4(value):
    try:
        ip = ipaddress.IPv4Address(value)
        return ip.is_global and not any(ip in net for net in SPECIAL)
    except (ValueError, TypeError):
        return False


def resolve_public(host):
    """Refuse the entire DNS answer if any candidate is unsafe."""
    if type(host) is not str or not HOST.fullmatch(host):
        raise ValueError("unapproved destination")
    rows = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM,
                              socket.IPPROTO_TCP)
    if not rows or len(rows)>32:
        raise ValueError("invalid resolution")
    addresses = []
    for family, kind, protocol, _, address in rows:
        if (family != socket.AF_INET or kind != socket.SOCK_STREAM
                or protocol != socket.IPPROTO_TCP or type(address) is not tuple
                or len(address)!=2 or address[1]!=443 or not public_ipv4(address[0])):
            raise PermissionError("non-public resolution refused")
        addresses.append(address)
    # One validated numerical address, no fallback or second name lookup.
    return addresses[0]


class PublicHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, port=443, *, timeout=5, context=None):
        if type(host) is not str or not HOST.fullmatch(host) or port!=443:
            raise ValueError("unapproved HTTPS destination")
        # Do not trust caller-supplied insecure SSL contexts.
        if context is None:
            context=ssl.create_default_context()
        if not context.check_hostname or context.verify_mode!=ssl.CERT_REQUIRED:
            raise ValueError("verified TLS required")
        super().__init__(host,port,timeout=timeout,context=context)
        self._public_context=context

    def set_tunnel(self, *args, **kwargs):
        raise PermissionError("tunnels prohibited")

    def connect(self):
        raw=None
        try:
            address=resolve_public(self.host)
            raw=socket.socket(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP)
            raw.settimeout(self.timeout)
            # socket.connect receives a numeric IPv4 tuple; no second DNS lookup.
            raw.connect(address)
            if raw.getpeername()!=address:
                raise PermissionError("unexpected peer")
            # Verify the original approved DNS name, never the numeric address.
            self.sock=self._public_context.wrap_socket(raw,server_hostname=self.host)
        except Exception as exc:
            if raw is not None:
                raw.close()
            logger.warning("Public HTTPS connection refused (%s)",type(exc).__name__)
            raise
