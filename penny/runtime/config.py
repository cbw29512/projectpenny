"""Private file configuration; no credentials in CLI arguments or logs."""
from dataclasses import dataclass,field
import json
import logging
import os
import stat

from psycopg.conninfo import conninfo_to_dict

logger=logging.getLogger(__name__)

@dataclass(frozen=True,slots=True)
class Config:
    dsn: str=field(repr=False)
    host: str | None=None
    key: bytes | None=field(default=None,repr=False)


def load_config(path,kind):
    fd=None
    try:
        if kind not in ("inference","bridge"):
            raise ValueError("unknown runtime")
        # Reject links, nonregular files, other owners and group/world access.
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        info=os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                or info.st_mode&0o077 or info.st_size>8192):
            raise PermissionError("unsafe configuration file")
        with os.fdopen(fd,"rb") as stream:
            fd=None
            raw=stream.read(8193)
        if len(raw)>8192:
            raise ValueError("oversized config")
        data=json.loads(raw)
        keys={"dsn"} if kind=="inference" else {"dsn","host","bridge_key_hex"}
        if type(data) is not dict or set(data)!=keys or type(data["dsn"]) is not str:
            raise ValueError("invalid config")
        fields=conninfo_to_dict(data["dsn"])
        # Only dedicated local database, no service indirection or hostaddr.
        if (fields.get("host")!="127.0.0.1" or fields.get("dbname")!="penny"
                or not fields.get("user") or set(fields)-{"host","port","dbname","user","password"}):
            raise ValueError("dedicated local database required")
        if kind=="inference":
            return Config(data["dsn"])
        if type(data["host"]) is not str or type(data["bridge_key_hex"]) is not str:
            raise ValueError("invalid bridge config")
        key=bytes.fromhex(data["bridge_key_hex"])
        if len(key)<32:
            raise ValueError("invalid bridge key")
        return Config(data["dsn"],data["host"],key)
    except Exception as exc:
        logger.error("Private runtime configuration rejected (%s)",type(exc).__name__)
        raise
    finally:
        if fd is not None:
            os.close(fd)
