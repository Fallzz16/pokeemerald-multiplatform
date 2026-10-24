"""Assert six-route probe preserves all inherited hub checks and source anchors."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
    imported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported)
    return imported


hub = module("extend_hub_party_qa")
routes = module("extend_six_routes_qa")


def fixture():
    original = ('require("lib").new(S, "HubPassReCross")\n'
                + "\n".join(anchor for anchor, _ in hub.REPLACEMENTS)
                + '\nlocal function maleJourney()\n'
                + 'F.run(function()\n  maleJourney()\n'
                + '  if booted then mayJourney() end\n  F.finish()\nend)')
    return hub.build(original)


class RealRegionalGateTests(unittest.TestCase):
    def test_six_ordered_travel_pairs_inherit_all_prior_assertions(self):
        source = fixture()
        rendered = routes.build(source)
        self.assertEqual(rendered.count("gwRunSixRoutes()"), 2)
        for origin, dest in [("Hoenn", "Kanto"), ("Kanto", "Johto"),
                             ("Johto", "Hoenn"), ("Hoenn", "Johto"),
                             ("Johto", "Kanto"), ("Kanto", "Hoenn")]:
            self.assertIn('"' + origin + ' to ' + dest + '"', rendered)
        self.assertIn("GW exactly six directed region transitions completed", rendered)
        self.assertIn("GW Pokemon struct size is 100", rendered)
        self.assertNotIn('new(S, "HubPassReCross")', rendered)

    def test_drift_is_rejected_without_partially_writing(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "GrandWorldHubParty.lua", Path(d) / "GrandWorldSixRoutes.lua"
            src.write_text("not an upstream hub suite")
            with self.assertRaisesRegex(ValueError, "identifier drift"):
                routes.prepare(src, dst)
            self.assertFalse(dst.exists())
            src.write_text(fixture())
            routes.prepare(src, dst)
            self.assertIn('GrandWorldSixRoutes', dst.read_text())
            with self.assertRaisesRegex(ValueError, "exists"):
                routes.prepare(src, dst)


if __name__ == "__main__":
    unittest.main()
