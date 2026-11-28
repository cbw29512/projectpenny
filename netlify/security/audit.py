"""Read-only effective privilege preflight for the dedicated mailbox schema."""
from dataclasses import dataclass
import logging

from .roles import NAME, SCOPES

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AuditResult:
    ready: bool
    issues: tuple[str, ...]


def audit_role(conn, schema, role, scope):
    # No credentials or arbitrary SQL in results. Scope is operator-selected.
    if (type(schema) is not str or not NAME.fullmatch(schema)
            or schema in ("public", "pg_catalog", "information_schema")
            or schema.startswith("pg_temp_")
            or type(role) is not str or not NAME.fullmatch(role)
            or scope not in SCOPES):
        raise ValueError("invalid audit target")
    try:
        issues = []
        row = conn.execute(
            """SELECT r.oid, r.rolsuper OR r.rolcreaterole OR r.rolcreatedb
                       OR r.rolreplication OR r.rolbypassrls,
                      EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m WHERE m.member=r.oid),
                      n.nspowner=r.oid,
                      pg_catalog.has_schema_privilege(r.oid,n.oid,'USAGE'),
                      pg_catalog.has_schema_privilege(r.oid,n.oid,'CREATE'),
                      o.rolsuper OR o.rolcreaterole OR o.rolcreatedb
                        OR o.rolreplication OR o.rolbypassrls OR o.rolcanlogin
               FROM pg_catalog.pg_roles r CROSS JOIN pg_catalog.pg_namespace n
               JOIN pg_catalog.pg_roles o ON o.oid=n.nspowner
               WHERE r.rolname=%s AND n.nspname=%s""", (role,schema)
        ).fetchone()
        if row is None:
            return AuditResult(False,("missing_role_or_schema",))
        oid,privileged,membership,owner,usage,create,unsafe_owner=row
        for flag,reason in (
            (privileged,"privileged_role"),(membership,"role_membership"),
            (owner,"schema_owner"),(not usage,"missing_schema_usage"),
            (create,"schema_create"),(unsafe_owner,"unsafe_schema_owner")
        ):
            if flag:
                issues.append(reason)
        # Includes effective PUBLIC and column-only grants (not just ACL rows).
        for name, in conn.execute(
            """SELECT c.relname FROM pg_catalog.pg_class c
               JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
               WHERE n.nspname=%s AND c.relkind IN ('r','p','v','m','f')
                 AND (c.relowner=%s OR
                      pg_catalog.has_table_privilege(%s::oid,c.oid,
                          'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                      OR pg_catalog.has_any_column_privilege(%s::oid,c.oid,
                          'SELECT,INSERT,UPDATE,REFERENCES'))
               ORDER BY c.relname""",(schema,oid,oid,oid)
        ).fetchall():
            issues.append("direct_relation:"+name)
        for name, in conn.execute(
            """SELECT c.relname FROM pg_catalog.pg_class c
               JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
               WHERE n.nspname=%s AND c.relkind='S'
                 AND (c.relowner=%s OR pg_catalog.has_sequence_privilege(
                      %s::oid,c.oid,'USAGE,SELECT,UPDATE')) ORDER BY c.relname""",
            (schema,oid,oid)
        ).fetchall():
            issues.append("direct_sequence:"+name)
        allowed=set()
        for signature in SCOPES[scope]:
            target=conn.execute("SELECT pg_catalog.to_regprocedure(%s)::oid",
                                (schema+"."+signature,)).fetchone()[0]
            if target is None:
                issues.append("missing_routine:"+signature)
            else:
                allowed.add(target)
        for fn,name,owned,execute,grantable,definer,owner_ok,path in conn.execute(
            """SELECT p.oid,p.proname,p.proowner=%s,
                      pg_catalog.has_function_privilege(%s::oid,p.oid,'EXECUTE'),
                      pg_catalog.has_function_privilege(%s::oid,p.oid,'EXECUTE WITH GRANT OPTION'),
                      p.prosecdef,p.proowner=n.nspowner,p.proconfig
               FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
               WHERE n.nspname=%s ORDER BY p.proname,p.oid""",
            (oid,oid,oid,schema)
        ).fetchall():
            if owned or grantable or (execute and fn not in allowed):
                issues.append("excess_routine:"+name)
            if fn in allowed:
                if not execute:
                    issues.append("missing_execute:"+name)
                if not definer or not owner_ok or path != [
                    "search_path=pg_catalog, "+schema+", pg_temp"
                ]:
                    issues.append("unsafe_routine:"+name)
        return AuditResult(not issues,tuple(issues))
    except Exception as exc:
        logger.error("Mailbox privilege audit unavailable (%s)",type(exc).__name__)
        raise
