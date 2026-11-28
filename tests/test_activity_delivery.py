"""Persistent attempt budget; synthetic configuration and mocked transport."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from database_fixture import DSN,DatabaseFixture
from penny.progress.delivery_gate import configure, reserve,clear_interrupted
from penny.progress.publisher import publish_once
from penny.runtime.operator_control import stop
from penny.scheduler.storage_db import locked


@unittest.skipUnless(DSN,"disposable PostgreSQL not configured")
class DeliveryTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.cfg=SimpleNamespace(dsn=self.dsn,host="fixture.netlify.app",key=b"x"*32)

    def age_cooldown(self):
        with locked(self.dsn) as (conn,_,now):
            conn.execute("UPDATE activity_delivery_control SET not_before=0")

    @patch("penny.progress.publisher._send_once",return_value="published")
    def test_default_closed_budget_cooldown_and_stop(self,send):
        self.assertEqual(publish_once(self.cfg,confirmed=True),"paused")
        self.assertFalse(configure(self.cfg,enabled=True,limit=1))
        self.assertTrue(configure(self.cfg,enabled=True,limit=1,confirmed=True))
        self.assertEqual(publish_once(self.cfg,confirmed=True),"published")
        self.assertEqual(publish_once(self.cfg,confirmed=True),"cooldown")
        self.age_cooldown()
        self.assertEqual(publish_once(self.cfg,confirmed=True),"budget_exhausted")
        self.assertTrue(configure(self.cfg,enabled=True,limit=1,confirmed=True))
        self.assertEqual(publish_once(self.cfg,confirmed=True),"budget_exhausted")
        stop(self.dsn)
        self.assertEqual(publish_once(self.cfg,confirmed=True),"paused")
        send.assert_called_once()

    @patch("penny.progress.publisher._send_once",return_value="backoff")
    def test_failure_disables_and_config_change_refused(self,send):
        self.assertTrue(configure(self.cfg,enabled=True,limit=10,confirmed=True))
        other=SimpleNamespace(dsn=self.dsn,host=self.cfg.host,key=b"y"*32)
        self.assertEqual(publish_once(other,confirmed=True),"paused")
        self.assertEqual(publish_once(self.cfg,confirmed=True),"backoff")
        self.assertEqual(publish_once(self.cfg,confirmed=True),"paused")
        self.assertTrue(configure(self.cfg,enabled=True,limit=10,confirmed=True))
        self.assertEqual(publish_once(self.cfg,confirmed=True),"cooldown")
        send.assert_called_once()

    @patch("penny.progress.publisher._send_once")
    def test_crash_requires_review_without_refunding_attempt(self,send):
        self.assertTrue(configure(self.cfg,enabled=True,limit=1,confirmed=True))
        self.assertEqual(reserve(self.cfg),"reserved")
        self.assertEqual(publish_once(self.cfg,confirmed=True),"review_required")
        self.assertFalse(clear_interrupted(self.dsn))
        self.assertTrue(clear_interrupted(self.dsn,confirmed=True))
        self.assertTrue(configure(self.cfg,enabled=True,limit=1,confirmed=True))
        self.age_cooldown()
        self.assertEqual(publish_once(self.cfg,confirmed=True),"budget_exhausted")
        send.assert_not_called()
