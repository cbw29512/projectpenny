"""Explicit remote database credential validation shared by operator and probes."""
import os
import re
from psycopg.conninfo import conninfo_to_dict
from .roles import NAME

HOST=re.compile(r"(?=.{1,253}\Z)[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\Z")


def validate_dsn(dsn,*,database,role):
    if any(k.startswith("PG") for k in os.environ):
        raise PermissionError("ambient PostgreSQL environment refused")
    if (type(database) is not str or not NAME.fullmatch(database)
            or database in ("penny","penny_test") or type(role) is not str
            or not NAME.fullmatch(role) or type(dsn) is not str):
        raise ValueError("explicit cloud database and role required")
    fields=conninfo_to_dict(dsn)
    host=fields.get("host","")
    port=fields.get("port","5432")
    if (set(fields)-{"host","port","dbname","user","password","sslmode","sslrootcert"}
            or fields.get("dbname")!=database or fields.get("user")!=role
            or fields.get("sslmode")!="verify-full" or not HOST.fullmatch(host)
            or "." not in host or host.lower().endswith(".localhost")
            or not fields.get("password") or not fields.get("sslrootcert")
            or not re.fullmatch(r"[0-9]{1,5}",port) or not 1<=int(port)<=65535):
        raise ValueError("explicit verified-TLS cloud DSN required")
    return dsn
