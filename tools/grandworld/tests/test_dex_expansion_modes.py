"""Guard deterministic Gen4 pilot vs optional twelve-family Gen5 capacity trial."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "dex", Path(__file__).resolve().parents[1] / "expand_gen4_pilot.py")
dex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dex)


class DexExpansionModesTests(unittest.TestCase):
    def test_unique_families_and_three_region_distribution(self):
        self.assertEqual(len(dex.PILOT), 31)
        self.assertEqual(len(dex.GEN5_PILOT), 12)
        self.assertEqual(len(set(dex.PILOT + dex.GEN5_PILOT)), 43)
        self.assertEqual(set(dex.GEN5_TRIAL_ROUTES), {"KANTO", "JOHTO", "HOENN"})
        for region, routes in dex.GEN5_TRIAL_ROUTES.items():
            with self.subTest(region=region):
                self.assertEqual(len(routes), 4)
                self.assertEqual(len(set(routes)), 4)
                self.assertTrue(all(route.startswith("MAP_ROUTE") for route, _ in routes))
        self.assertNotIn("ARCEUS", dex.GEN5_PILOT)

    def test_trial_never_becomes_default(self):
        import inspect
        sig = inspect.signature(dex.patch)
        self.assertIs(sig.parameters["gen5_trial"].default, False)


if __name__ == "__main__":
    unittest.main()
