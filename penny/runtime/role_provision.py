"""Explicit trusted-owner provisioning; never invoked by workers."""
import logging
from psycopg import sql
from .role_state import SCOPES,valid_name,valid_schema
from .role_audit import audit_role

logger=logging.getLogger(__name__)


def configure_roles(conn,schema,*,inference,bridge,projection,confirmed=False):
    try:
        mapping=dict(inference=inference,bridge=bridge,projection=projection)
        if (confirmed is not True or not valid_schema(schema)
                or not all(valid_name(r) for r in mapping.values())
                or len(set(mapping.values()))!=3):
            raise ValueError("explicit confirmation and separate roles required")
        with conn.transaction():
            owner=conn.execute(
                """SELECT r.oid,r.rolname,r.rolsuper OR r.rolcreaterole OR r.rolcreatedb
                   OR r.rolreplication OR r.rolbypassrls OR r.rolcanlogin,
                   EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m WHERE m.member=r.oid)
                   FROM pg_catalog.pg_namespace n JOIN pg_catalog.pg_roles r ON r.oid=n.nspowner
                   WHERE n.nspname=%s AND r.rolname=current_user""",(schema,)).fetchone()
            if owner is None or owner[2] or owner[3]:
                raise PermissionError("dedicated non-login schema owner required")
            for role in mapping.values():
                row=conn.execute(
                    """SELECT r.oid,r.rolsuper OR r.rolcreaterole OR r.rolcreatedb
                       OR r.rolreplication OR r.rolbypassrls,
                       EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m WHERE m.member=r.oid),
                       pg_catalog.has_schema_privilege(r.oid,%s,'CREATE')
                       FROM pg_catalog.pg_roles r WHERE r.rolname=%s""",(schema,role)).fetchone()
                if row is None or row[0]==owner[0] or any(row[1:]):
                    raise PermissionError("unsafe runtime role")
            # Dedicated application schema only. Remove PUBLIC access before
            # granting fixed entrypoints, including old trigger helpers.
            ns=sql.Identifier(schema)
            for statement in ("REVOKE ALL ON SCHEMA {} FROM PUBLIC",
                              "REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM PUBLIC",
                              "REVOKE ALL ON ALL SEQUENCES IN SCHEMA {} FROM PUBLIC",
                              "REVOKE ALL ON ALL FUNCTIONS IN SCHEMA {} FROM PUBLIC"):
                conn.execute(sql.SQL(statement).format(ns))
            for scope,role in mapping.items():
                target=sql.Identifier(role)
                # Do not silently grant around an unsafe pre-existing role.
                # Audit after grants; any excess privilege rolls all changes back.
                conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(ns,target))
                for signature in SCOPES[scope]:
                    conn.execute(sql.SQL("GRANT EXECUTE ON FUNCTION {}.{} TO {}").format(
                        ns,sql.SQL(signature),target))
            reports={scope:audit_role(conn,schema,role,scope) for scope,role in mapping.items()}
            if not all(r.ready for r in reports.values()):
                raise PermissionError("effective local privilege audit refused")
            return reports
    except Exception as exc:
        logger.error("Local role provisioning refused (%s)",type(exc).__name__)
        raise
