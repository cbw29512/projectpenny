"""Trusted owner-only fresh mailbox installation. Never run in a web function."""
import logging
import re

from psycopg import sql
from psycopg.pq import TransactionStatus
from .manifest import release_plan
from .roles import NAME,SCOPES,configure_roles
from .audit import audit_role

logger=logging.getLogger(__name__)
LOCK=724390581215035


def install_fresh(conn,*,database,schema,roles,expected_digest,confirmed=False):
    """Atomic install into an empty pre-created schema; no upgrade or reset path."""
    try:
        if (confirmed is not True or type(database) is not str or not database
                or database=="penny" or type(schema) is not str
                or (schema!="penny_mailbox" and not (
                    database=="penny_test" and re.fullmatch(r"mailbox_[a-f0-9]{32}",schema)))
                or type(roles) is not dict or set(roles)!=set(SCOPES)
                or not all(type(r) is str and NAME.fullmatch(r) for r in roles.values())
                or len(set(roles.values()))!=len(roles)
                or not conn.autocommit or conn.info.transaction_status!=TransactionStatus.IDLE):
            raise ValueError("explicit fresh-install target and idle owner connection required")
        digest,entries=release_plan()
        if expected_digest!=digest:
            raise ValueError("release digest does not match reviewed migrations")
        with conn.transaction():
            conn.execute("SET LOCAL statement_timeout='30s'")
            conn.execute("SET LOCAL lock_timeout='5s'")
            if conn.execute("SELECT current_database()").fetchone()[0]!=database:
                raise PermissionError("wrong target database")
            if not conn.execute("SELECT pg_try_advisory_xact_lock(%s)",(LOCK,)).fetchone()[0]:
                raise RuntimeError("mailbox installation busy")
            owner=conn.execute("""SELECT r.rolname,r.rolsuper OR r.rolcreaterole OR r.rolcreatedb
                OR r.rolreplication OR r.rolbypassrls OR r.rolcanlogin,
                EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m WHERE m.member=r.oid)
                FROM pg_catalog.pg_namespace n JOIN pg_catalog.pg_roles r ON r.oid=n.nspowner
                WHERE n.nspname=%s AND r.rolname=current_user""",(schema,)).fetchone()
            if not owner or owner[1] or owner[2] or owner[0] in roles.values():
                raise PermissionError("dedicated non-login owner required")
            # Reject any existing objects including an earlier migration ledger.
            occupied=conn.execute("""SELECT EXISTS(
                SELECT 1 FROM pg_catalog.pg_depend d
                JOIN pg_catalog.pg_namespace n ON n.oid=d.refobjid
                WHERE n.nspname=%s AND d.refclassid='pg_catalog.pg_namespace'::regclass
                AND d.deptype IN ('n','a','i'))""",(schema,)).fetchone()[0]
            if occupied:
                raise PermissionError("schema not empty; no upgrade or overwrite supported")
            ns=sql.Identifier(schema)
            conn.execute(sql.SQL("SET LOCAL search_path TO {}, pg_catalog, pg_temp").format(ns))
            conn.execute(sql.SQL("REVOKE ALL ON SCHEMA {} FROM PUBLIC").format(ns))
            # A migration failure rolls back every earlier migration in this install.
            for _,_,body in entries:
                conn.execute(body)
            conn.execute("""CREATE TABLE mailbox_install_manifest (
                name text PRIMARY KEY, sha256 text NOT NULL CHECK(sha256 ~ '^[a-f0-9]{64}$'),
                release_sha256 text NOT NULL CHECK(release_sha256 ~ '^[a-f0-9]{64}$'))""")
            for name,sha,_ in entries:
                conn.execute("INSERT INTO mailbox_install_manifest VALUES (%s,%s,%s)",(name,sha,digest))
            for statement in ("REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM PUBLIC",
                              "REVOKE ALL ON ALL SEQUENCES IN SCHEMA {} FROM PUBLIC",
                              "REVOKE ALL ON ALL FUNCTIONS IN SCHEMA {} FROM PUBLIC"):
                conn.execute(sql.SQL(statement).format(ns))
            configure_roles(conn,schema,**roles)
            for scope,role in roles.items():
                if not audit_role(conn,schema,role,scope).ready:
                    raise PermissionError("runtime privilege audit failed")
            # All public data paths must be disabled at commit, not just at boot.
            if conn.execute("""SELECT
                (SELECT enabled FROM mailbox_control WHERE singleton),
                (SELECT enabled FROM activity_observation WHERE singleton),
                (SELECT enabled FROM workshop_observation WHERE singleton)""").fetchone()!=(False,False,False):
                raise PermissionError("initial publication gates not closed")
            return {"status":"installed_disabled","migration_count":len(entries),
                    "release_sha256":digest,"production_certified":False}
    except Exception as exc:
        logger.error("Mailbox fresh installation refused (%s)",type(exc).__name__)
        raise
