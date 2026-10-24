"""Guard real-hub mGBA instrumenter against drift and accidental test weakening."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / "extend_hub_party_qa.py"
spec = importlib.util.spec_from_file_location("hub_party", path)
hub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hub)


def pinned_shape_fixture():
    # Exact individual anchors are verified against pinned World when applied in CI.
    # Assemble a minimal shape that exercises ALL transformations independently.
    return 'require("lib").new(S, "HubPassReCross")\n' + "\n".join(
        anchor for anchor, _ in hub.REPLACEMENTS
    )


class HubPartyProbeTests(unittest.TestCase):
    def test_seven_real_gate_checkpoints_and_unchanged_existing_checks(self):
        raw = pinned_shape_fixture()
        updated = hub.build(raw)
        self.assertEqual(updated.count('gwTravelProbe('), 8)
        self.assertIn('new(S, "GrandWorldHubParty")', updated)
        self.assertIn('gwTravelProbe("after real male Hoenn re-cross"', updated)
        self.assertIn('gwTravelProbe("female second real Hoenn gate"', updated)
        self.assertIn('F.check("S4 first cross as MAY landed in MAY\'s 2F', updated)

    def test_missing_or_duplicated_anchor_fails_closed(self):
        raw = pinned_shape_fixture()
        anchor = hub.REPLACEMENTS[2][0]
        for bad in (raw.replace(anchor, ""), raw + anchor):
            with self.subTest(bad=bad[-90:]):
                with self.assertRaisesRegex(ValueError, "drift"):
                    hub.build(bad)

    def test_never_overwrites_existing_suite(self):
        with tempfile.TemporaryDirectory() as t:
            source, dest = Path(t) / "HubPassReCross.lua", Path(t) / "GrandWorldHubParty.lua"
            source.write_text(pinned_shape_fixture())
            hub.prepare(source, dest)
            self.assertIn('GrandWorldHubParty', dest.read_text())
            dest.write_text("do not replace me")
            with self.assertRaisesRegex(ValueError, "already exists"):
                hub.prepare(source, dest)
            self.assertEqual(dest.read_text(), "do not replace me")


if __name__ == "__main__":
    unittest.main()
