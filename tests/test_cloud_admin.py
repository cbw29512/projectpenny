"""Cloud administration is retired; only trusted schema owner provisions mailbox."""
import unittest
import psycopg
from uuid import uuid4
from database_fixture import DSN
from cloud_role_fixture import CloudRoleFixture
from netlify.security.roles import SCOPES


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class NoCloudAdminTests(CloudRoleFixture):
    def test_retired_routines_and_no_admin_runtime_scope(self):
        self.assertNotIn("admin",SCOPES)
        for name in ("mailbox_admin_status(uuid)","mailbox_admin_pause(uuid)",
                     "mailbox_admin_allow(uuid,text)"):
            self.assertEqual(self.call("owner","SELECT to_regprocedure(%s)",name),[(None,)])
        for role in ("member","bridge","maintenance","projection_writer","projection_reader","admin"):
            for query in ("SELECT * FROM mailbox_admin_event",
                          "UPDATE mailbox_control SET enabled=false RETURNING enabled"):
                with self.subTest(role=role,query=query):
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        self.call(role,query)

    def test_owner_only_provisioning_preserves_normal_mailbox(self):
        self.call("owner","UPDATE mailbox_control SET enabled=false RETURNING enabled")
        self.assertEqual(self.call("member","SELECT * FROM mailbox_submit(%s,%s,%s)",
                                   self.a,uuid4(),"Question")[0][0],"paused")
        self.call("owner","UPDATE mailbox_control SET enabled=true RETURNING enabled")
        self.assertEqual(self.call("member","SELECT * FROM mailbox_submit(%s,%s,%s)",
                                   self.a,uuid4(),"Question")[0][0],"accepted")
