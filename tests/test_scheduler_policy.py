import unittest
from dataclasses import replace

from penny.scheduler.policy import admission, next_task
from penny.scheduler.state import Admission, QueueSnapshot, TaskSpec, Tier

NOW = 1000


def job(task_id, member=None, tier=None, submitted=990, expires=3000):
    return TaskSpec(task_id, member, tier, submitted, expires)


class PolicyTests(unittest.TestCase):
    def test_reserved_class_capacity(self):
        free = tuple(job(str(i), f"member{i}", Tier.FREE) for i in range(3))
        state = QueueSnapshot(waiting=free)
        self.assertEqual(admission(state, job("x", "x", Tier.FREE), NOW), Admission.FULL)
        self.assertEqual(admission(state, job("paid", "x", Tier.GOLD), NOW), Admission.ACCEPT)
        self.assertEqual(admission(state, job("internal"), NOW), Admission.ACCEPT)

    def test_all_ten_slots(self):
        free = tuple(job(f"f{i}", f"f{i}", Tier.FREE) for i in range(3))
        paid = tuple(job(f"p{i}", f"p{i}", Tier.GOLD) for i in range(5))
        business = (job("b1"), job("b2"))
        state = QueueSnapshot(waiting=free + paid + business)
        for task in (job("b3"), job("p6", "p6", Tier.INNER_CIRCLE), job("f4", "f4", Tier.FREE)):
            self.assertEqual(admission(state, task, NOW), Admission.FULL)

    def test_active_counts_toward_member_cap(self):
        state = QueueSnapshot(active=job("active", "u", Tier.FREE))
        self.assertEqual(admission(state, job("new", "u", Tier.FREE), NOW), Admission.MEMBER_LIMIT)

    def test_supporter_caps(self):
        state = QueueSnapshot(waiting=(job("a", "u", Tier.GOLD), job("b", "u", Tier.GOLD)))
        self.assertEqual(admission(state, job("c", "u", Tier.GOLD), NOW), Admission.MEMBER_LIMIT)
        self.assertEqual(admission(state, job("c", "u", Tier.PLATINUM), NOW), Admission.ACCEPT)

    def test_no_preemption(self):
        state = QueueSnapshot(active=job("active"), waiting=(job("high", "u", Tier.INNER_CIRCLE),))
        self.assertIsNone(next_task(state, NOW))

    def test_priority_within_supporter_class(self):
        low, high = job("low", "a", Tier.COPPER), job("high", "b", Tier.GOLD)
        self.assertEqual(next_task(QueueSnapshot(waiting=(low, high)), NOW), high)

    def test_equal_priority_stable_order(self):
        a, b = job("a", "x", Tier.GOLD), job("b", "y", Tier.GOLD)
        self.assertEqual(next_task(QueueSnapshot(waiting=(b, a)), NOW), a)

    def test_compute_share(self):
        b, p, f = job("b"), job("p", "p", Tier.GOLD), job("f", "f", Tier.FREE)
        state = QueueSnapshot(waiting=(b, p, f), business_seconds=60, supporter_seconds=30)
        self.assertEqual(next_task(state, NOW), f)
        self.assertEqual(next_task(replace(state, free_seconds=10), NOW), b)

    def test_unused_capacity(self):
        f = job("f", "f", Tier.FREE)
        self.assertEqual(next_task(QueueSnapshot(waiting=(f,), free_seconds=999), NOW), f)

    def test_aging_overrides_priority(self):
        old, new = job("old", "a", Tier.COPPER, submitted=0), job("new", "b", Tier.INNER_CIRCLE)
        self.assertEqual(next_task(QueueSnapshot(waiting=(new, old)), NOW), old)

    def test_avoid_repeat_when_alternative(self):
        high, low = job("h", "a", Tier.INNER_CIRCLE), job("l", "b", Tier.COPPER)
        self.assertEqual(next_task(QueueSnapshot(waiting=(high, low), last_member_id="a"), NOW), low)

    def test_expired_never_dispatched(self):
        expired = job("e", "e", Tier.GOLD, expires=NOW)
        self.assertIsNone(next_task(QueueSnapshot(waiting=(expired,)), NOW))
        self.assertEqual(admission(QueueSnapshot(), expired, NOW), Admission.EXPIRED)

    def test_pause(self):
        task = job("b")
        state = QueueSnapshot(paused=True, waiting=(task,))
        self.assertIsNone(next_task(state, NOW))
        self.assertEqual(admission(state, job("c"), NOW), Admission.PAUSED)

    def test_invalid_identity_and_tier(self):
        state = QueueSnapshot()
        for task in (job("a", "u", None), job("b", None, Tier.GOLD), job("c", "u", 99)):
            self.assertEqual(admission(state, task, NOW), Admission.INVALID)

    def test_duplicate_id(self):
        task = job("a")
        self.assertEqual(admission(QueueSnapshot(waiting=(task,)), task, NOW), Admission.DUPLICATE_ID)

    def test_corrupt_snapshot_fails_closed(self):
        task = job("a")
        state = QueueSnapshot(waiting=(task, task))
        with self.assertLogs("penny.scheduler.policy", level="WARNING"):
            self.assertEqual(admission(state, job("b"), NOW), Admission.INVALID)
        with self.assertLogs("penny.scheduler.policy", level="ERROR"):
            self.assertIsNone(next_task(state, NOW))


if __name__ == "__main__":
    unittest.main()
