"""Disposable PostgreSQL role/schema fixture; no provider credentials."""
from pathlib import Path
import unittest
from uuid import uuid4

import psycopg
from psycopg import sql
from database_fixture import DSN
from netlify.security.roles import configure_roles


class CloudRoleFixture(unittest.TestCase):
    def setUp(self):
        suffix=uuid4().hex
        self.schema="mailbox_"+suffix
        self.roles={k:k+"_"+suffix for k in ("owner","member","bridge","maintenance","admin","outsider","projection_writer","projection_reader")}
        self.addCleanup(self.cleanup_roles)
        with psycopg.connect(DSN,autocommit=True) as conn:
            if conn.info.dbname!="penny_test":
                raise RuntimeError("disposable database required")
            for role in self.roles.values():
                conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(role)))
            conn.execute(sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
                sql.Identifier(self.schema),sql.Identifier(self.roles["owner"])))
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(self.roles["owner"])))
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
            for path in sorted(Path("netlify/mailbox").glob("*.sql")):
                conn.execute(path.read_text())
            configure_roles(conn,self.schema,**{k:self.roles[k] for k in ("member","bridge","maintenance","admin","projection_writer","projection_reader")})
            conn.execute("UPDATE mailbox_control SET enabled=true")
            self.a,self.b=uuid4(),uuid4()
            conn.execute("INSERT INTO mailbox_member(id) VALUES (%s),(%s)",(self.a,self.b))

    def call(self,role,query,*args):
        with psycopg.connect(DSN) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(self.roles[role])))
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
            return conn.execute(query,args).fetchall()

    def cleanup_roles(self):
        with psycopg.connect(DSN,autocommit=True) as conn:
            if conn.info.dbname!="penny_test":
                raise RuntimeError("disposable database required")
            conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema)))
            for role in self.roles.values():
                conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))
