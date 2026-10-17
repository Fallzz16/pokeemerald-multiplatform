"""Self-tests of Auto QA selection, Windows skip semantics, and failure reporting."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("emerald_auto_qa", ROOT / "tools" / "emerald_auto_qa.py")
Q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Q)


class AutoQARunner(unittest.TestCase):
    def test_rejects_unbounded_repetitions(self):
        for n in (0, 21):
            with self.assertRaises(ValueError):
                Q.run(ROOT, group="lab", repeats=n)

    def test_rejects_missing_source_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                Q.run(Path(tmp), group="lab")

    def test_windows_native_posix_tests_explicitly_skipped(self):
        events = []
        def fake_execute(root, pattern, timeout):
            events.append(pattern)
            return {"suite": pattern, "status": "PASS", "exit_code": 0,
                    "seconds": 0.0, "output": "mocked"}
        with patch.object(Q.os, "name", "nt"), patch.object(Q, "execute", side_effect=fake_execute):
            summary = Q.run(ROOT, group="protocol")
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["skipped"], 2)
        self.assertNotIn("test_ehl8_native_bridge.py", events)
        self.assertNotIn("test_ehl8_native_reconnect.py", events)

    def test_failed_suite_is_reported_without_false_success(self):
        def fail(root, pattern, timeout):
            return {"suite": pattern, "status": "FAIL", "exit_code": 1,
                    "seconds": 0.0, "output": "intentional mock failure"}
        with patch.object(Q, "execute", side_effect=fail):
            summary = Q.run(ROOT, group="lab")
        self.assertGreater(summary["failed"], 0)
        self.assertEqual(summary["passed"], 0)


if __name__ == "__main__":
    unittest.main()
