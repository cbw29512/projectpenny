"""Resolve ownership under the same transaction as the memory operation."""
from contextlib import contextmanager

from penny.scheduler.storage_db import locked
from .session import resolve_member


@contextmanager
def member_scope(dsn, member_id, session_token):
    # Raw UUID path remains for trusted internal repository callers only.
    # Public-facing adapters must exclusively use token resolution.
    if session_token is not None and member_id is not None:
        raise ValueError("ambiguous member identity")
    with locked(dsn) as (conn,control,now):
        owner = resolve_member(conn,now,session_token) if session_token is not None else member_id
        yield conn,control,now,owner
