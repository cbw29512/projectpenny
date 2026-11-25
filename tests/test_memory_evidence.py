import unittest
from hashlib import sha256
from uuid import UUID, uuid4

from penny.memory.evidence import fingerprint, MAX_EVIDENCE_BYTES


class EvidenceTests(unittest.TestCase):
    def test_fingerprint_is_deterministic_and_bound_to_source(self):
        source = uuid4()
        result = fingerprint(source, b"observed result")
        self.assertEqual(result.source_task_id, source)
        self.assertEqual(result.digest, sha256(b"observed result").hexdigest())
        self.assertEqual(result.byte_count, 15)
        self.assertEqual(result, fingerprint(source, b"observed result"))
        self.assertNotEqual(result, fingerprint(uuid4(), b"observed result"))
        self.assertNotEqual(result.digest, fingerprint(source, b"changed").digest)

    def test_invalid_inputs(self):
        for source, material in (
            (None, b"x"), (str(uuid4()), b"x"), (UUID(int=0), b"x"),
            (uuid4(), b""), (uuid4(), "text"), (uuid4(), bytearray(b"x")),
            (uuid4(), b"x" * (MAX_EVIDENCE_BYTES + 1)),
        ):
            with self.subTest(source_type=type(source), material_type=type(material)):
                with self.assertRaises(ValueError):
                    fingerprint(source, material)

    def test_inclusive_size_limit(self):
        self.assertEqual(fingerprint(uuid4(), b"x" * MAX_EVIDENCE_BYTES).byte_count,
                         MAX_EVIDENCE_BYTES)
