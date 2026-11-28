"""Read one protected operator credential file, never an ambient provider URL."""
from dataclasses import dataclass,field
import logging

from penny.runtime.config import read_config
from .credentials import validate_dsn
from .roles import NAME,SCOPES

logger=logging.getLogger(__name__)


@dataclass(frozen=True,slots=True)
class OperatorConfig:
    database: str
    login: str
    dsn: str=field(repr=False)
    owner: str|None=None
    roles: dict|None=None
    scope: str|None=None


def load(path,kind):
    try:
        data=read_config(path)
        base={"database","login","dsn"}
        keys=base|({"owner","roles"} if kind=="install" else {"scope"})
        if kind not in ("install","probe") or type(data) is not dict or set(data)!=keys:
            raise ValueError("invalid cloud operator configuration")
        validate_dsn(data["dsn"],database=data["database"],role=data["login"])
        if kind=="install":
            owner,roles=data["owner"],data["roles"]
            if (type(owner) is not str or not NAME.fullmatch(owner)
                    or type(roles) is not dict or set(roles)!=set(SCOPES)
                    or not all(type(r) is str and NAME.fullmatch(r) for r in roles.values())
                    or len({owner,data["login"],*roles.values()})!=7):
                raise ValueError("separate installer, owner and runtime roles required")
            return OperatorConfig(data["database"],data["login"],data["dsn"],owner,roles)
        if data["scope"] not in SCOPES:
            raise ValueError("invalid runtime scope")
        return OperatorConfig(data["database"],data["login"],data["dsn"],scope=data["scope"])
    except Exception as exc:
        logger.error("Cloud operator configuration refused (%s)",type(exc).__name__)
        raise
