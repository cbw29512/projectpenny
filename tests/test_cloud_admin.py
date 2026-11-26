"""Restricted SQL administration; private test database only."""
import unittest
from uuid import uuid4

import psycopg
from database_fixture import DSN
from cloud_role_fixture import CloudRoleFixture


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class CloudAdminTests(CloudRoleFixture):
    def setUp(self):
        super().setUp()
        self.admin=uuid4()
        self.call("owner","INSERT INTO mailbox_admin(id) VALUES (%s) RETURNING id",self.admin)

    def test_admin_status_and_idempotent_pause(self):
        q=self.call("member","SELECT * FROM mailbox_submit(%s,%s,%s)",self.a,uuid4(),"Question")[0][1]
        self.assertEqual(self.call("admin","SELECT * FROM mailbox_admin_status(%s)",self.admin),[(True,1,0)])
        for _ in range(2):
            self.assertEqual(self.call("admin","SELECT mailbox_admin_pause(%s)",self.admin),[(True,)])
        self.assertEqual(self.call("owner","SELECT count(*) FROM mailbox_admin_event"),[(1,)])
        self.assertEqual(self.call("admin","SELECT * FROM mailbox_admin_status(%s)",self.admin),[(False,1,0)])
        self.assertEqual(self.call("bridge","SELECT * FROM mailbox_claim()"),[])
        self.assertEqual(self.call("member","SELECT * FROM mailbox_submit(%s,%s,%s)",self.b,uuid4(),"Hi")[0][0],"paused")
        self.assertEqual(self.call("member","SELECT * FROM mailbox_read(%s,%s)",self.a,q),[(q,"submitted",None)])

    def test_member_and_disabled_admin_not_authorized(self):
        self.assertEqual(self.call("admin","SELECT * FROM mailbox_admin_status(%s)",self.a),[])
        self.assertEqual(self.call("admin","SELECT mailbox_admin_pause(%s)",self.a),[(False,)])
        self.call("owner","UPDATE mailbox_admin SET enabled=false WHERE id=%s RETURNING id",self.admin)
        self.assertEqual(self.call("admin","SELECT mailbox_admin_pause(%s)",self.admin),[(False,)])
        self.assertEqual(self.call("owner","SELECT enabled FROM mailbox_control"),[(True,)])

    def test_role_boundaries(self):
        for role,query,args in [
            ("member","SELECT mailbox_admin_pause(%s)",(self.admin,)),
            ("bridge","SELECT * FROM mailbox_admin_status(%s)",(self.admin,)),
            ("maintenance","SELECT mailbox_admin_pause(%s)",(self.admin,)),
            ("admin","SELECT * FROM mailbox_question",()),
            ("admin","SELECT * FROM mailbox_claim()",()),
            ("admin","UPDATE mailbox_control SET enabled=true RETURNING enabled",()),
            ("admin","INSERT INTO mailbox_admin(id) VALUES (%s) RETURNING id",(uuid4(),)),
            ("admin","SELECT * FROM mailbox_admin_event",()),
        ]:
            with self.subTest(role=role,query=query):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    self.call(role,query,*args)
