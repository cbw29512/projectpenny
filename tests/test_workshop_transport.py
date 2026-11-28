"""Disposable cloud projection security and freshness."""
import time
import unittest
import psycopg
from database_fixture import DSN
from cloud_role_fixture import CloudRoleFixture


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class WorkshopTransportTests(CloudRoleFixture):
    def publish(self,n,stage="prototype_reviewed",generated=None,expiry=None):
        return self.call("projection_writer","SELECT workshop_publish(%s,%s,%s,%s)",
            n,stage,n-10 if generated is None else generated,n+100 if expiry is None else expiry)[0][0]

    def test_closed_monotonic_and_expiry(self):
        n=int(time.time())
        self.assertFalse(self.publish(n))
        self.call("owner","UPDATE workshop_observation SET enabled=true RETURNING enabled")
        self.assertFalse(self.publish(n-16))
        self.assertFalse(self.publish(n,expiry=n+121))
        self.assertTrue(self.publish(n))
        self.assertTrue(self.publish(n))
        self.assertFalse(self.publish(n,"revision_reviewed"))
        self.assertEqual(self.call("projection_reader","SELECT * FROM workshop_read()"),
                         [(n,"prototype_reviewed",n-10,n+100)])
        # Synthetic time ageing, not a wait or an extension of real data.
        self.call("owner","UPDATE workshop_observation SET sampled_at=%s,received_at=%s,generated_at=%s,expires_at=%s RETURNING singleton",
                  n-121,n-121,n-130,n-21)
        self.assertEqual(self.call("projection_reader","SELECT * FROM workshop_read()"),[])
        self.assertTrue(self.publish(int(time.time()),"unavailable",0,0))
        self.assertEqual(self.call("projection_reader","SELECT * FROM workshop_read()"),[])

    def test_roles_cannot_cross_read_write_or_access_table(self):
        for role,query in (("projection_reader","SELECT workshop_publish(1,'unavailable',0,0)"),
                           ("projection_writer","SELECT * FROM workshop_read()"),
                           ("projection_reader","SELECT * FROM workshop_observation"),
                           ("member","SELECT * FROM workshop_read()"),
                           ("bridge","SELECT workshop_publish(1,'unavailable',0,0)")):
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                self.call(role,query)
