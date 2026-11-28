"""Read-only verification of the actual service login, not an owner connection."""
import logging
import psycopg

from .role_audit import audit_role
from .role_state import SCOPES,RoleAudit,valid_name,valid_schema

logger=logging.getLogger(__name__)


def inspect_connection(conn,schema,role,scope):
    """Catalog checks only; never execute worker entrypoints during preflight."""
    try:
        if not valid_schema(schema) or not valid_name(role) or scope not in SCOPES:
            raise ValueError("invalid runtime target")
        # The default role search path is critical: worker SQL calls are
        # intentionally unqualified and config rejects arbitrary DSN options.
        row=conn.execute(
            """SELECT current_user,session_user,current_schemas(false),
               r.rolcanlogin,
               pg_catalog.has_database_privilege(r.oid,d.oid,'CREATE'),
               pg_catalog.has_database_privilege(r.oid,d.oid,'TEMP'),
               d.datdba=r.oid
               FROM pg_catalog.pg_roles r CROSS JOIN pg_catalog.pg_database d
               WHERE r.rolname=current_user AND d.datname=current_database()""").fetchone()
        if row is None:
            return RoleAudit(False,("missing_runtime_login",))
        user,session,path,can_login,create,temp,owns_db=row
        issues=[]
        for flag,label in (
            (user!=role or session!=role or not can_login,"wrong_runtime_login"),
            (list(path) not in ([schema],["pg_catalog",schema]),"unsafe_runtime_search_path"),
            (create or owns_db,"database_create_or_owner"),
            (temp,"database_temp")):
            if flag:
                issues.append(label)
        # A restricted runtime needs no other application namespace.
        # PostgreSQL system catalogs remain accessible by design.
        extra=conn.execute(
            """SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_namespace n
               WHERE n.nspname<>%s AND n.nspname<>'information_schema'
                 AND NOT starts_with(n.nspname,'pg_')
                 AND (pg_catalog.has_schema_privilege(current_user,n.oid,'USAGE')
                   OR pg_catalog.has_schema_privilege(current_user,n.oid,'CREATE')))""",
            (schema,)).fetchone()[0]
        if extra:
            issues.append("other_application_schema_access")
        report=audit_role(conn,schema,role,scope)
        issues.extend(report.issues)
        return RoleAudit(not issues,tuple(issues))
    except Exception as exc:
        logger.error("Runtime login inspection failed (%s)",type(exc).__name__)
        raise


def probe_login(dsn,schema,role,scope):
    try:
        with psycopg.connect(dsn,connect_timeout=5) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute("SET LOCAL statement_timeout='5s'")
            conn.execute("SET LOCAL lock_timeout='5s'")
            return inspect_connection(conn,schema,role,scope)
    except Exception as exc:
        logger.warning("Runtime login probe unavailable (%s)",type(exc).__name__)
        return RoleAudit(False,("login_probe_unavailable",))
