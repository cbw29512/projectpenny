"""Private file configuration; no credentials in CLI arguments or logs."""
from dataclasses import dataclass,field
import json
import logging
import os
from pathlib import Path
import re
import stat

from psycopg.conninfo import conninfo_to_dict

from penny.bridge.public_https import HOST

logger=logging.getLogger(__name__)
HEX_KEY=re.compile(r"[0-9a-fA-F]{64,128}\Z")
PORT=re.compile(r"[0-9]{1,5}\Z")


@dataclass(frozen=True,slots=True)
class Config:
    dsn: str=field(repr=False)
    host: str | None=None
    key: bytes | None=field(default=None,repr=False)


def unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError("duplicate configuration key")
        result[key]=value
    return result


def read_config(path):
    # Pin the immediate parent directory before opening a file relative to it.
    # A deployment must independently protect the ancestors and release tree.
    path=Path(path)
    directory=None
    fd=None
    try:
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        parent=os.fstat(directory)
        if parent.st_uid!=os.getuid() or parent.st_mode&0o022:
            raise PermissionError("unsafe configuration directory")
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        info=os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                or info.st_mode&0o7077 or info.st_nlink!=1 or not 1<=info.st_size<=8192):
            raise PermissionError("unsafe configuration file")
        with os.fdopen(fd,"rb") as stream:
            fd=None
            raw=stream.read(8193)
            after=os.fstat(stream.fileno())
        # Refuse a file modified during the read.
        if (not 1<=len(raw)<=8192 or len(raw)!=info.st_size
                or (info.st_size,info.st_mtime_ns,info.st_ctime_ns)!=
                   (after.st_size,after.st_mtime_ns,after.st_ctime_ns)):
            raise ValueError("unstable configuration file")
        return json.loads(raw.decode("utf-8"),object_pairs_hook=unique_pairs)
    finally:
        if fd is not None:
            os.close(fd)
        if directory is not None:
            os.close(directory)


def load_config(path,kind):
    try:
        if kind not in ("inference","bridge","operator","projection"):
            raise ValueError("unknown runtime")
        # libpq uses PG* environment settings for omitted connection options,
        # including hostaddr, service, options, password files and TLS. Refuse
        # the ambient namespace rather than maintaining an incomplete list.
        if any(name.startswith("PG") for name in os.environ):
            raise PermissionError("ambient PostgreSQL environment refused")
        data=read_config(path)
        key_field="projection_key_hex" if kind=="projection" else "bridge_key_hex"
        keys={"dsn"} if kind in ("inference","operator") else {"dsn","host",key_field}
        if type(data) is not dict or set(data)!=keys or type(data["dsn"]) is not str:
            raise ValueError("invalid config")
        fields=conninfo_to_dict(data["dsn"])
        # Only dedicated local database, no service indirection or hostaddr.
        if (fields.get("host")!="127.0.0.1" or fields.get("dbname")!="penny"
                or not fields.get("user") or set(fields)-{"host","port","dbname","user","password"}):
            raise ValueError("dedicated local database required")
        port=fields.get("port","5432")
        if not PORT.fullmatch(port) or not 1<=int(port)<=65535:
            raise ValueError("invalid database port")
        if kind in ("inference","operator"):
            return Config(data["dsn"])
        if (type(data["host"]) is not str or not HOST.fullmatch(data["host"])
                or type(data[key_field]) is not str or not HEX_KEY.fullmatch(data[key_field])):
            raise ValueError("invalid outbound config")
        key=bytes.fromhex(data[key_field])
        if not 32<=len(key)<=64:
            raise ValueError("invalid outbound key")
        return Config(data["dsn"],data["host"],key)
    except Exception as exc:
        # Only the error category is logged; driver errors may include secrets.
        logger.error("Private runtime configuration rejected (%s)",type(exc).__name__)
        raise
