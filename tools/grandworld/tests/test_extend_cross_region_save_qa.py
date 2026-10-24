"""Ensure save-after-six-routes QA retains the real itinerary and nine probes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hub = load("extend_hub_party_qa")
routes = load("extend_six_routes_qa")
saved = load("extend_cross_region_save_qa")


class CrossRegionSaveTests(unittest.TestCase):
    @staticmethod
    def sample():
        base = 'require("lib").new(S, "GrandWorldHubParty")\n'
        base += 'local function maleJourney()\n'
        base += '  if booted then mayJourney() end\n  F.finish()\n'
        return routes.build(base)

    def test_real_six_routes_preserved_and_nine_save_checks_added(self):
        previous = self.sample()
        new = saved.build(previous)
        self.assertIn('GrandWorldCrossRegionSave', new)
        self.assertEqual(new.count('F.check("GW cross-region'), 9)
        self.assertEqual(new.count('gwRunSixRoutes()'), previous.count('gwRunSixRoutes()'))
        self.assertIn('client.reboot_core()', new)
        self.assertIn('F.selectStartIcon(7)', new)
        self.assertIn('gwPartyFingerprint() == beforeParty', new)
        self.assertIn('gwHeroVar() == beforeHero', new)
        self.assertEqual(new.count('GW exactly six directed region transitions completed'), 1)
        for name in ("Hoenn to Kanto", "Kanto to Johto", "Johto to Hoenn",
                     "Hoenn to Johto", "Johto to Kanto", "Kanto to Hoenn"):
            self.assertIn(name, new)

    def test_drift_and_output_overwrite_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            a, b = d / "GrandWorldSixRoutes.lua", d / "GrandWorldCrossRegionSave.lua"
            a.write_text("bad")
            with self.assertRaisesRegex(ValueError, "drift"):
                saved.prepare(a, b)
            self.assertFalse(b.exists())
            a.write_text(self.sample())
            saved.prepare(a, b)
            b.write_text("existing evidence")
            with self.assertRaisesRegex(ValueError, "already exists"):
                saved.prepare(a, b)
            self.assertEqual(b.read_text(), "existing evidence")


if __name__ == "__main__":
    unittest.main()
