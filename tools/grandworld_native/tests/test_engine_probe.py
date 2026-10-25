"""Small deterministic tests for genuine World object-inventory reporting."""
from pathlib import Path
import tempfile
import unittest

from tools.grandworld_native.engine_probe import compile_engine, SOURCES


class EngineProbeTests(unittest.TestCase):
    def test_all_sources_uses_actual_count_not_default_24(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "src").mkdir()
            for name in ("main.c", "region_switch.c", "extra_module.c"):
                (root / "src" / name).write_text("int placeholder;\n", encoding="utf-8")
            result = compile_engine(
                root, root / "output", compiler="missing-gw-compiler",
                use_preproc=False, all_sources=True
            )
            self.assertEqual(result["requested"], 3)
            self.assertEqual(len(result["objects"]), 3)
            self.assertTrue(result["all_sources_requested"])
            self.assertFalse(result["world_engine_linked"])
            self.assertFalse(result["world_gameplay_booted"])

    def test_initial_slice_stays_on_real_world_sources(self):
        self.assertIn("main.c", SOURCES)
        self.assertIn("main_menu.c", SOURCES)
        self.assertIn("follower_npc.c", SOURCES)
        self.assertIn("load_save.c", SOURCES)


if __name__ == "__main__":
    unittest.main()
