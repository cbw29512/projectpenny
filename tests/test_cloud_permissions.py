"""Exercise real restricted PostgreSQL roles, not mocked authorization."""
import unittest
from uuid import uuid4

import psycopg
from psycopg import sql
from database_fixture import DSN
from cloud_role_fixture import CloudRoleFixture
from netlify.security.roles import configure_roles


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class CloudPermissionTests(CloudRoleFixture):
    def submit(self):
        return self.call("member","SELECT * FROM mailbox_submit(%s,%s,%s)",self.a,uuid4(),"Hi")[0][1]

    def deny(self,role,query,*args):
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.call(role,query,*args)

    def test_member_cannot_read_raw_records_or_administer(self):
        q=self.submit()
        self.assertEqual(self.call("member","SELECT * FROM mailbox_read(%s,%s)",self.b,q),[])
        self.deny("member","SELECT * FROM mailbox_question")
        self.deny("member","UPDATE mailbox_control SET enabled=false RETURNING enabled")
        self.deny("member","INSERT INTO mailbox_member(id) VALUES (%s) RETURNING id",uuid4())
        self.deny("member","SELECT * FROM mailbox_claim()")
        self.deny("member","SELECT mailbox_purge()")
        self.deny("member","SELECT mailbox_expire(clock_timestamp())")

    def test_bridge_can_deliver_but_not_submit_read_or_administer(self):
        q=self.submit()
        claimed=self.call("bridge","SELECT * FROM mailbox_claim()")[0]
        self.assertEqual(claimed[0],q)
        self.assertTrue(self.call("bridge","SELECT mailbox_ack(%s,%s,%s)",q,claimed[3],uuid4())[0][0])
        self.assertTrue(self.call("bridge","SELECT mailbox_answer(%s,%s,%s)",q,claimed[3],"reply")[0][0])
        self.assertEqual(self.call("member","SELECT * FROM mailbox_read(%s,%s)",self.a,q),[(q,"answered","reply")])
        self.deny("bridge","SELECT * FROM mailbox_read(%s,%s)",self.a,q)
        self.deny("bridge","SELECT * FROM mailbox_submit(%s,%s,%s)",self.b,uuid4(),"forged")
        self.deny("bridge","SELECT * FROM mailbox_member")
        self.deny("bridge","SELECT mailbox_purge()")

    def test_maintenance_and_outsider_are_restricted(self):
        self.assertEqual(self.call("maintenance","SELECT mailbox_purge()"),[(0,)])
        self.deny("maintenance","SELECT * FROM mailbox_claim()")
        self.deny("maintenance","SELECT * FROM mailbox_question")
        with psycopg.connect(DSN) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(self.roles["outsider"])))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute(sql.SQL("SELECT {}.mailbox_claim()").format(sql.Identifier(self.schema)))

    def test_temp_table_cannot_shadow_trusted_control(self):
        with psycopg.connect(DSN) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(self.roles["member"])))
            conn.execute("CREATE TEMP TABLE mailbox_control(singleton boolean,enabled boolean)")
            conn.execute("INSERT INTO mailbox_control VALUES(true,false)")
            conn.execute(sql.SQL("SET search_path TO pg_temp, {}").format(sql.Identifier(self.schema)))
            result=conn.execute(sql.SQL("SELECT * FROM {}.mailbox_submit(%s,%s,%s)").format(
                sql.Identifier(self.schema)),(self.a,uuid4(),"Hi")).fetchone()
            self.assertEqual(result[0],"accepted")

    def test_runtime_roles_cannot_create_objects(self):
        for role in ("member","bridge","maintenance"):
            self.deny(role,"CREATE TABLE unauthorized(id integer)")

    def test_provision_rejects_unsafe_or_shared_roles(self):
        with psycopg.connect(DSN) as conn:
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(self.roles["owner"])))
            with self.assertRaises(ValueError):
                configure_roles(conn,self.schema,member=self.roles["member"],
                                bridge=self.roles["member"],maintenance=self.roles["maintenance"])
            with self.assertRaises(PermissionError):
                configure_roles(conn,self.schema,member=self.roles["owner"],
                                bridge=self.roles["bridge"],maintenance=self.roles["maintenance"])
