"""Operator-only role grant plan; never invoked by a public handler."""
import logging
import re

from psycopg import sql

logger = logging.getLogger(__name__)
# Fixed signatures, not supplied by a request or the model.
SCOPES = {
    "member": ("mailbox_submit(uuid,uuid,text)","mailbox_read(uuid,uuid)",
               "mailbox_allow_member(uuid,text)","community_mailbox_submit(uuid,uuid,text)"),
    "bridge": ("mailbox_claim()","mailbox_ack(uuid,uuid,uuid)",
               "mailbox_answer(uuid,uuid,text)","mailbox_reject(uuid,uuid)",
               "mailbox_allow_bridge(text)","community_mailbox_claim()","community_mailbox_ack(uuid,uuid)"),
    "maintenance": ("mailbox_purge()",),
    "projection_writer": ("activity_publish(bigint,text)","workshop_publish(bigint,text,bigint,bigint)","workshop_allow_write()"),
    "projection_reader": ("activity_read()","workshop_read()","workshop_allow_read()"),
}
HELPER = "mailbox_expire(timestamptz)"
NAME = re.compile(r"[a-z][a-z0-9_]{0,62}")


def configure_roles(conn, schema, *, member, bridge, maintenance,
                    projection_writer=None, projection_reader=None):
    """Grant narrow execution on a dedicated schema in one transaction.

    Roles must already exist; no passwords or account creation here.
    The caller must run as the dedicated non-login schema/function owner.
    Refuse role membership, privileged flags and preexisting schema access
    that could defeat this simple least-privilege model.
    """
    try:
        mapping = dict(member=member,bridge=bridge,maintenance=maintenance)
        if (projection_writer is None) != (projection_reader is None):
            raise ValueError("separate paired projection roles required")
        if projection_writer is not None:
            mapping.update(projection_writer=projection_writer,projection_reader=projection_reader)
        names = [schema,*mapping.values()]
        if any(type(n) is not str or not NAME.fullmatch(n) for n in names):
            raise ValueError("invalid role or schema name")
        if len(set(mapping.values())) != len(mapping) or schema in ("public","pg_catalog","information_schema"):
            raise ValueError("separate roles and dedicated schema required")
        with conn.transaction():
            owner = conn.execute(
                """SELECT r.rolname,r.rolsuper,r.rolcreaterole,r.rolcreatedb,
                          r.rolreplication,r.rolbypassrls,r.rolcanlogin
                   FROM pg_catalog.pg_namespace n JOIN pg_catalog.pg_roles r
                     ON r.oid=n.nspowner
                   WHERE n.nspname=%s AND r.rolname=current_user""",(schema,)
            ).fetchone()
            if owner is None or any(owner[1:]):
                raise PermissionError("dedicated non-login owner required")
            for role in mapping.values():
                row = conn.execute(
                    """SELECT r.rolsuper,r.rolcreaterole,r.rolcreatedb,
                              r.rolreplication,r.rolbypassrls,
                              EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m
                                     WHERE m.member=r.oid),
                              pg_catalog.has_schema_privilege(r.oid,%s,'CREATE')
                       FROM pg_catalog.pg_roles r WHERE r.rolname=%s""",(schema,role)
                ).fetchone()
                if role == owner[0] or row is None or any(row):
                    raise PermissionError("unsafe runtime role")
            # Remove direct table grants and all mailbox function grants before
            # applying the explicit allowlist; no user input becomes SQL text.
            ns = sql.Identifier(schema)
            for scope,role in mapping.items():
                target = sql.Identifier(role)
                conn.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM {}").format(ns,target))
                conn.execute(sql.SQL("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA {} FROM {}").format(ns,target))
                conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(ns,target))
                for signature in SCOPES[scope]:
                    conn.execute(sql.SQL("GRANT EXECUTE ON FUNCTION {}.{} TO {}").format(
                        ns,sql.SQL(signature),target))
    except Exception as exc:
        logger.error("Mailbox role provisioning refused (%s)",type(exc).__name__)
        raise
