"""Regression tests for the strict M8 ROM evidence contract."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "qa_acceptance.py"
spec = importlib.util.spec_from_file_location("grandworld_qa", MODULE_PATH)
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)

SHA = "a" * 64
SIZE = 33554432
MEM = {"ROM": 25000000, "EWRAM": 230000, "IWRAM": 30000}


class EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "evidence.json"
        self.valid = {"sha": SHA, "rom_size": SIZE, "memory": MEM}

    def write(self, obj):
        self.path.write_text(json.dumps(obj), encoding="utf-8")

    def test_matching_sha_size_and_memory(self):
        self.write(self.valid)
        self.assertEqual(qa.load_memory_proof(self.path, SHA, SIZE), MEM)

    def test_missing_or_incorrect_size(self):
        for obj in ({**self.valid, "rom_size": SIZE - 1},
                    {k: v for k, v in self.valid.items() if k != "rom_size"},
                    {**self.valid, "rom_size": str(SIZE)}):
            with self.subTest(obj=obj):
                self.write(obj)
                with self.assertRaisesRegex(ValueError, "different ROM"):
                    qa.load_memory_proof(self.path, SHA, SIZE)

    def test_divergent_hash(self):
        self.write({**self.valid, "sha": "b" * 64})
        with self.assertRaisesRegex(ValueError, "different ROM"):
            qa.load_memory_proof(self.path, SHA, SIZE)

    def test_legacy_size_evidence_rejected(self):
        self.write({"sha": SHA, "size": SIZE, "memory": MEM})
        with self.assertRaisesRegex(ValueError, "different ROM"):
            qa.load_memory_proof(self.path, SHA, SIZE)

    def test_invalid_json_and_invalid_results(self):
        for data in ("{invalid", "[]", "null", json.dumps({**self.valid, "memory": []})):
            with self.subTest(data=data):
                self.path.write_text(data, encoding="utf-8")
                with self.assertRaises(ValueError):
                    qa.load_memory_proof(self.path, SHA, SIZE)
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "invalid memory evidence file"):
            qa.load_memory_proof(self.path, SHA, SIZE)


if __name__ == "__main__":
    unittest.main()
