"""Read-only cloud login preflight; inspect the actual authenticated connection."""
import logging
import re
import psycopg
from .credentials import validate_dsn
from .audit import AuditResult,audit_role
from .roles import NAME,SCOPES

logger=logging.getLogger(__name__)


def inspect_connection(conn,*,database,schema,role,scope,require_tls=True):
    try:
        if (type(database) is not str or not database or database=="penny"
                or type(schema) is not str or (schema!="penny_mailbox" and not
                    (database=="penny_test" and re.fullmatch(r"mailbox_[a-f0-9]{32}",schema)))
                or type(role) is not str or not NAME.fullmatch(role)
                or scope not in SCOPES or type(require_tls) is not bool
                or (not require_tls and database!="penny_test")):
            raise ValueError("invalid cloud login target")
        row=conn.execute("""SELECT current_database(),current_user,session_user,
            r.rolcanlogin,current_schemas(true),pg_my_temp_schema(),
            pg_catalog.has_database_privilege(r.oid,d.oid,'CREATE'),
            pg_catalog.has_database_privilege(r.oid,d.oid,'TEMP'),d.datdba=r.oid,
            COALESCE((SELECT ssl FROM pg_catalog.pg_stat_ssl
                      WHERE pid=pg_backend_pid()),false)
            FROM pg_catalog.pg_roles r CROSS JOIN pg_catalog.pg_database d
            WHERE r.rolname=current_user AND d.datname=current_database()""").fetchone()
        if row is None:
            return AuditResult(False,("missing_cloud_login",))
        db,user,session,can_login,path,temp_schema,create,temp,owner,tls=row
        issues=[]
        for flag,label in (
            (db!=database,"wrong_database"),
            (user!=role or session!=role or not can_login,"wrong_runtime_login"),
            (list(path) not in (["pg_catalog"],["pg_catalog",schema]) or temp_schema!=0,
             "unsafe_search_path"),
            (create or owner,"database_create_or_owner"),
            (temp,"database_temp"),
            (require_tls and not tls,"tls_required"),
        ):
            if flag:
                issues.append(label)
        extra=conn.execute("""SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_namespace n
            WHERE n.nspname<>%s AND n.nspname<>'information_schema'
            AND NOT starts_with(n.nspname::text,'pg_')
            AND (pg_catalog.has_schema_privilege(current_user,n.oid,'USAGE')
                 OR pg_catalog.has_schema_privilege(current_user,n.oid,'CREATE')))""",
            (schema,)).fetchone()[0]
        if extra:
            issues.append("other_application_schema_access")
        issues.extend(audit_role(conn,schema,role,scope).issues)
        return AuditResult(not issues,tuple(issues))
    except Exception as exc:
        logger.error("Cloud login inspection refused (%s)",type(exc).__name__)
        raise


def probe_login(dsn,*,database,role,scope):
    """Only explicit verified-TLS DSNs; never use ambient owner connection."""
    try:
        validate_dsn(dsn,database=database,role=role)
        with psycopg.connect(dsn,connect_timeout=5) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute("SET LOCAL statement_timeout='5s'")
            conn.execute("SET LOCAL lock_timeout='5s'")
            return inspect_connection(conn,database=database,schema="penny_mailbox",
                                      role=role,scope=scope)
    except Exception as exc:
        logger.warning("Cloud login probe unavailable (%s)",type(exc).__name__)
        return AuditResult(False,("cloud_login_probe_unavailable",))
