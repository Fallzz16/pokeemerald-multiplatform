"""Check six independent valid hero save suites and fail-closed output handling."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


story = load("extend_story_save_qa")
matrix = load("generate_hero_save_matrix")


def source_fixture():
    return story.build("\n".join(anchor for anchor, _ in story.REPLACEMENTS))


class SixHeroMatrixTests(unittest.TestCase):
    def test_exact_six_both_genders_and_four_save_checks(self):
        original = source_fixture()
        self.assertEqual([s for _, s, _ in matrix.HEROES], list(range(6)))
        for name, slot, gender in matrix.HEROES:
            with self.subTest(hero=name):
                lua = matrix.render(original, name, slot, gender)
                self.assertIn("GrandWorldSave" + name, lua)
                self.assertIn("gwBeforeSaveHero == " + str(slot), lua)
                self.assertIn("S.SaveBlock2.playerGender) == " + str(gender), lua)
                self.assertIn("GW real save/Continue preserved " + name + " hero", lua)
                self.assertEqual(lua.count("GW real save/Continue preserved"), 4)

    def test_source_drift_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "drift"):
            matrix.render("missing source", "Red", 2, 0)

    def test_no_suite_overwrites_and_six_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            source = directory / "GrandWorldHeroSave.lua"
            source.write_text(source_fixture())
            created = matrix.prepare(source, directory)
            self.assertEqual(len(created), 6)
            (directory / created[0]).write_text("preserve")
            with self.assertRaisesRegex(ValueError, "already exist"):
                matrix.prepare(source, directory)
            self.assertEqual((directory / created[0]).read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
