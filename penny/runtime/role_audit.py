"""Read-only effective privilege check within the dedicated Penny schema."""
import logging
from .role_state import SCOPES,RoleAudit,valid_name,valid_schema

logger=logging.getLogger(__name__)


def audit_role(conn,schema,role,scope):
    try:
        if not valid_schema(schema) or not valid_name(role) or scope not in SCOPES:
            raise ValueError("invalid role audit target")
        row=conn.execute(
            """SELECT r.oid,n.nspowner,
               r.rolsuper OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolbypassrls,
               EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m WHERE m.member=r.oid),
               pg_catalog.has_schema_privilege(r.oid,n.oid,'USAGE'),
               pg_catalog.has_schema_privilege(r.oid,n.oid,'CREATE'),
               o.rolsuper OR o.rolcreaterole OR o.rolcreatedb OR o.rolreplication OR o.rolbypassrls OR o.rolcanlogin,
               EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m WHERE m.member=o.oid)
               FROM pg_catalog.pg_roles r CROSS JOIN pg_catalog.pg_namespace n
               JOIN pg_catalog.pg_roles o ON o.oid=n.nspowner
               WHERE r.rolname=%s AND n.nspname=%s""",(role,schema)).fetchone()
        if row is None:
            return RoleAudit(False,("missing_role_or_schema",))
        oid,owner,privileged,membership,usage,create,unsafe_owner,owner_membership=row
        issues=[label for flag,label in (
            (privileged,"privileged_role"),(membership,"role_membership"),
            (oid==owner,"schema_owner"),(not usage,"missing_schema_usage"),
            (create,"schema_create"),(unsafe_owner or owner_membership,"unsafe_schema_owner"))
            if flag]
        # Effective PUBLIC grants and column-only privileges count too.
        for name,kind in conn.execute(
            """SELECT c.relname,c.relkind FROM pg_catalog.pg_class c
               JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
               WHERE n.nspname=%s AND
               CASE WHEN c.relkind='S' THEN c.relowner=%s OR
                    pg_catalog.has_sequence_privilege(%s::oid,c.oid,'USAGE,SELECT,UPDATE')
               WHEN c.relkind IN ('r','p','v','m','f') THEN c.relowner=%s OR
                    pg_catalog.has_table_privilege(%s::oid,c.oid,
                      'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                    OR pg_catalog.has_any_column_privilege(%s::oid,c.oid,
                      'SELECT,INSERT,UPDATE,REFERENCES')
               ELSE false END ORDER BY c.relname""",(schema,oid,oid,oid,oid,oid)).fetchall():
            issues.append(("direct_sequence:" if kind=="S" else "direct_relation:")+name)
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
               WHERE n.nspname=%s ORDER BY p.proname,p.oid""",(oid,oid,oid,schema)).fetchall():
            if owned or grantable or (execute and fn not in allowed):
                issues.append("excess_routine:"+name)
            if fn in allowed:
                if not execute:
                    issues.append("missing_execute:"+name)
                if not definer or not owner_ok or path!=["search_path=pg_catalog, "+schema+", pg_temp"]:
                    issues.append("unsafe_routine:"+name)
        return RoleAudit(not issues,tuple(issues))
    except Exception as exc:
        logger.error("Local role audit failed (%s)",type(exc).__name__)
        raise
