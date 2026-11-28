"""Atomic installation in disposable PostgreSQL; never contact Netlify."""
import unittest
from uuid import uuid4
from unittest.mock import patch

import psycopg
from psycopg import sql
from database_fixture import DSN
from netlify.security.manifest import release_plan
from netlify.security.install import install_fresh
from netlify.security.roles import SCOPES


class ManifestTests(unittest.TestCase):
    def test_release_is_exact_order_and_digest(self):
        digest,entries=release_plan()
        self.assertEqual(len(entries),12)
        self.assertEqual(len(digest),64)
        self.assertEqual(digest,release_plan()[0])
        self.assertEqual(entries[0][0],"001_schema.sql")
        self.assertEqual(entries[-1][0],"012_community_admission.sql")


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class InstallTests(unittest.TestCase):
    def setUp(self):
        suffix=uuid4().hex
        self.schema="mailbox_"+suffix
        self.owner="owner_"+suffix
        self.roles={scope:scope+"_"+suffix for scope in SCOPES}
        self.conn=psycopg.connect(DSN,autocommit=True)
        self.addCleanup(self.conn.close)
        if self.conn.info.dbname!="penny_test":
            raise RuntimeError("disposable database required")
        self.addCleanup(self.cleanup)
        for role in [self.owner,*self.roles.values()]:
            self.conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(role)))
        self.conn.execute(sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
            sql.Identifier(self.schema),sql.Identifier(self.owner)))
        self.conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(self.owner)))

    def cleanup(self):
        self.conn.execute("RESET ROLE")
        self.conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.schema)))
        for role in [self.owner,*self.roles.values()]:
            self.conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))

    def install(self,**changes):
        args=dict(database="penny_test",schema=self.schema,roles=self.roles,
                  expected_digest=release_plan()[0],confirmed=True)
        return install_fresh(self.conn,**(args|changes))

    def query(self,statement):
        self.conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
        return self.conn.execute(statement).fetchall()

    def test_install_is_disabled_and_repeat_refuses_without_data_loss(self):
        report=self.install()
        self.assertEqual(report["migration_count"],12)
        self.assertFalse(report["production_certified"])
        self.assertEqual(self.query("SELECT count(*) FROM mailbox_install_manifest"),[(12,)])
        self.assertEqual(self.query("SELECT enabled FROM mailbox_control"),[(False,)])
        self.assertEqual(self.query("SELECT enabled FROM community_mailbox_control"),[(False,)])
        with self.assertRaises(PermissionError):
            self.install()
        self.assertEqual(self.query("SELECT count(*) FROM mailbox_install_manifest"),[(12,)])

    def test_bad_digest_and_existing_object_refuse(self):
        with self.assertRaises(ValueError):
            self.install(expected_digest="0"*64)
        self.conn.execute(sql.SQL("CREATE TABLE {}.existing_data(id integer)").format(sql.Identifier(self.schema)))
        with self.assertRaises(PermissionError):
            self.install()
        self.assertEqual(self.query("SELECT count(*) FROM existing_data"),[(0,)])

    def test_unexpected_enabled_community_gate_rolls_back(self):
        digest,entries=release_plan()
        # Simulate an unsafe migration while preserving the reviewed release input shape.
        name,sha,body=entries[-1]
        altered=entries[:-1]+((name,sha,body+"\nUPDATE community_mailbox_control SET enabled=true;"),)
        with patch("netlify.security.install.release_plan",return_value=(digest,altered)):
            with self.assertRaises(PermissionError):
                self.install()
        self.assertEqual(self.query("SELECT to_regclass('community_mailbox_control')"),[(None,)])

    def test_late_failure_rolls_back_all_migrations(self):
        with patch("netlify.security.install.audit_role",side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.install()
        self.assertEqual(self.query("SELECT to_regclass('mailbox_control')"),[(None,)])
        self.assertEqual(self.install()["status"],"installed_disabled")
