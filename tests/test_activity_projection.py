"""Dedicated projection roles and freshness; disposable DB only."""
import time
import unittest
import psycopg
from database_fixture import DSN
from cloud_role_fixture import CloudRoleFixture
from netlify.security.audit import audit_role


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class ActivityProjectionTests(CloudRoleFixture):
    def publish(self, sample, activity="working"):
        return self.call("projection_writer","SELECT activity_publish(%s,%s)",
                         sample,activity)[0][0]

    def read(self):
        return self.call("projection_reader","SELECT * FROM activity_read()")

    def enable(self):
        self.call("owner","UPDATE activity_observation SET enabled=true RETURNING enabled")

    def test_default_closed_monotonic_and_freshness(self):
        now=int(time.time())
        self.assertFalse(self.publish(now))
        self.assertEqual(self.read(),[])
        self.enable()
        self.assertFalse(self.publish(now-16))
        self.assertFalse(self.publish(now+60))
        self.assertFalse(self.publish(now,"private prompt"))
        self.assertTrue(self.publish(now))
        self.assertTrue(self.publish(now))
        self.assertFalse(self.publish(now,"idle"))
        self.assertFalse(self.publish(now-1))
        self.assertEqual(self.read(),[(now,"working")])
        # Age the fixture rather than waiting; old data cannot become fresh.
        self.call("owner","UPDATE activity_observation SET sampled_at=%s,received_at=%s RETURNING sampled_at",
                  now-121,now-121)
        self.assertEqual(self.read(),[])
        self.assertTrue(self.publish(int(time.time()),"idle"))

    def test_roles_are_isolated_and_audited(self):
        for role in ("projection_writer","projection_reader"):
            with psycopg.connect(DSN) as conn:
                report=audit_role(conn,self.schema,self.roles[role],role)
                self.assertTrue(report.ready,report.issues)
            for query in ("SELECT * FROM mailbox_question","SELECT * FROM activity_observation",
                          "SELECT * FROM mailbox_claim()"):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    self.call(role,query)
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.call("projection_reader","SELECT activity_publish(%s,%s)",int(time.time()),"idle")
        for role in ("member","bridge","admin","maintenance","projection_writer"):
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                self.call(role,"SELECT * FROM activity_read()")
