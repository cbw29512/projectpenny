"""Private audit data, never a public projection or a security certificate."""
from dataclasses import dataclass
import ipaddress
import re

USER=re.compile(r"[a-z_][a-z0-9_-]{0,31}\Z")
HOST=re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?\Z")
LAN=tuple(ipaddress.IPv4Network(n) for n in ("10.0.0.0/8","172.16.0.0/12","192.168.0.0/16"))


@dataclass(frozen=True,slots=True)
class DesktopScope:
    user: str
    desktop: str
    server: str
    host: str
    port: int=22

    def connection_spec(self):
        # Explicit operator inputs, never auto-approve the current SSH peer.
        if not USER.fullmatch(self.user) or self.user=="root" or not HOST.fullmatch(self.host):
            raise ValueError("invalid desktop scope")
        for value in (self.desktop,self.server):
            ip=ipaddress.IPv4Address(value)
            if not any(ip in net for net in LAN):
                raise ValueError("private LAN IPv4 address required")
        if self.desktop==self.server or type(self.port) is not int or not 1<=self.port<=65535:
            raise ValueError("invalid endpoint")
        return f"user={self.user},host={self.host},addr={self.desktop},laddr={self.server},lport={self.port}"


SSH_POLICY={
    "passwordauthentication":{"no"},
    "kbdinteractiveauthentication":{"no"},
    "pubkeyauthentication":{"yes"},
    "permitrootlogin":{"no"},
    "permitemptypasswords":{"no"},
    "hostbasedauthentication":{"no"},
    "authenticationmethods":{"publickey"},
    "disableforwarding":{"yes"},
    "permituserenvironment":{"no"},
    "permittunnel":{"no"},
    "x11forwarding":{"no"},
}


def ssh_findings(raw):
    fields={}
    for line in raw.splitlines():
        key,sep,value=line.partition(" ")
        if key in SSH_POLICY:
            if not sep or key in fields:
                raise ValueError("ambiguous ssh policy")
            fields[key]=value.strip().lower()
    return {key:("matches" if fields.get(key) in values else
                 "missing" if key not in fields else "review_required")
            for key,values in SSH_POLICY.items()}


def listener_findings(raw,ports,ssh_port):
    # ss -H -lnt returns LISTEN recv-q send-q local-address peer-address.
    rows=set()
    for line in raw.splitlines():
        columns=line.split()
        if len(columns)!=5 or columns[0]!="LISTEN":
            raise ValueError("unexpected listener output")
        host,sep,port=columns[3].rpartition(":")
        if not sep or not port.isascii() or not port.isdecimal() or not 1<=int(port)<=65535:
            raise ValueError("invalid listener port")
        address=host.strip("[]").split("%",1)[0]
        if address=="*":
            scope="wildcard"
        else:
            ip=ipaddress.ip_address(address)
            scope="wildcard" if ip.is_unspecified else "loopback" if ip.is_loopback else "nonloopback"
        number=int(port)
        # Do not disclose addresses or processes; all nonloopback bindings need review.
        if number in ports:
            role="protected_port"
        elif number==ssh_port:
            role="ssh_candidate"
        else:
            role="other_service"
        rows.add((number,scope,role))
    return [{"port":p,"binding":s,"category":r} for p,s,r in sorted(rows)]
