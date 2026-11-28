from datetime import datetime
import unittest
from penny.progress.rest_schedule import window_at


class RestScheduleTests(unittest.TestCase):
    def at(self, value):
        return window_at(int(datetime.fromisoformat(value).timestamp()))

    def test_midnight_and_wake(self):
        self.assertFalse(self.at("2026-11-26T23:59:59-05:00").scheduled_rest)
        self.assertTrue(self.at("2026-11-27T00:00:00-05:00").scheduled_rest)
        self.assertTrue(self.at("2026-11-27T07:59:59-05:00").scheduled_rest)
        self.assertFalse(self.at("2026-11-27T08:00:00-05:00").scheduled_rest)

    def test_dst_elapsed_duration(self):
        for start,hours in [("2026-03-08T00:00:00-05:00",7),
                            ("2026-11-01T00:00:00-04:00",9)]:
            self.assertEqual(self.at(start).next_transition-int(datetime.fromisoformat(start).timestamp()),hours*3600)
        self.assertIsNone(window_at(True))
