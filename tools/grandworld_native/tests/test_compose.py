import unittest
from pathlib import Path
from unittest.mock import patch
from tools.grandworld_native import compose


class CompositionTests(unittest.TestCase):
    def test_order_is_frozen(self):
        self.assertEqual([name for name, _ in compose.PATCHES],
                         ["integrate_world.py", "expand_gen4_pilot.py",
                          "add_hero_profiles.py", "add_kanto_avatar.py",
                          "optimize_overworld_budget.py", "apply_grass_only.py",
                          "translate_ptbr_stage1.py",
                          "adapt_ptbr_greedy_gifts_qa.py",
                          "adapt_ptbr_healthboxes_qa.py"])

    def test_wrong_pin_rejected(self):
        with patch.object(compose, "git", return_value="wrong-sha"):
            with self.assertRaises(RuntimeError):
                compose.check_source(Path("/none"), Path("/none"))

    def test_plan_never_applies_itself(self):
        commands = compose.make_commands(Path("/tmp/world"), Path("/tmp/grandworld"))
        self.assertEqual(len(commands), 9)
        self.assertTrue(commands[0][1].endswith("/integrate_world.py"))
        self.assertTrue(commands[-1][1].endswith("/adapt_ptbr_healthboxes_qa.py"))


if __name__ == "__main__":
    unittest.main()
