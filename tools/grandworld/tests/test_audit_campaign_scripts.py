"""Fail-closed structural checks for all 24 badge awards and 3 Hall of Fame paths."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "campaigns", Path(__file__).resolve().parents[1] / "audit_campaign_scripts.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def fixture(root):
    includes = []
    for region, names in audit.GYMS.items():
        for badge, gym in enumerate(names, 1):
            gympath = "data/maps/" + gym + "/scripts.inc"
            award = audit.badge_path(region, badge)
            for path in (gympath, award):
                p = root / path
                p.parent.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    p.write_text("")
                includes.append('\t.include "' + path + '"')
            with (root / award).open("a") as out:
                out.write("\tsetflag " + audit.flag_name(region, badge) + "\n")
    for region, (room, hall, champion, flag, warp) in audit.LEAGUE_PATHS.items():
        (root / room).parent.mkdir(parents=True, exist_ok=True)
        (root / room).write_text("warp " + warp + "\n")
        includes.append('\t.include "' + room + '"')
        p = root / hall
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("dofieldeffect FLDEFF_HALL_OF_FAME_RECORD\n")
        includes.append('\t.include "' + hall + '"')
        c = root / champion
        c.parent.mkdir(parents=True, exist_ok=True)
        with c.open("a") as out:
            out.write("setflag " + flag + "\n")
            if region == "johto":
                out.write("setflag " + flag + "\n")
    event = root / "data/event_scripts.s"
    event.parent.mkdir(parents=True, exist_ok=True)
    event.write_text("\n".join(includes))


class CampaignScriptAuditTests(unittest.TestCase):
    def test_24_real_award_seams_and_3_league_seams(self):
        with tempfile.TemporaryDirectory() as t:
            world = Path(t)
            fixture(world)
            proof = audit.audit(world)
            self.assertEqual(proof["badge_awards_found"], 24)
            self.assertEqual(proof["league_paths_found"], 3)
            self.assertFalse(proof["release_approved"])
            shrine = [b for b in proof["badges"]
                      if b["region"] == "johto" and b["badge"] == 8][0]
            self.assertIn("DragonsDen_Shrine", shrine["badge_award_script"])
            self.assertTrue(all(not b["gameplay_verified"] for b in proof["badges"]))

    def test_johto_shrine_and_duplicate_awards_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            world = Path(t)
            fixture(world)
            file = world / audit.badge_path("johto", 8)
            file.write_text("setflag FLAG_JOHTO_BADGE_7\n")
            with self.assertRaisesRegex(ValueError, "johto badge 8"):
                audit.audit(world)
            file.write_text("setflag FLAG_JOHTO_BADGE_8\nsetflag FLAG_JOHTO_BADGE_8\n")
            with self.assertRaisesRegex(ValueError, "badge 8"):
                audit.audit(world)

    def test_missing_champion_completion_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            world = Path(t)
            fixture(world)
            path = world / audit.LEAGUE_PATHS["kanto"][2]
            path.write_text("no champion flag")
            with self.assertRaisesRegex(ValueError, "kanto"):
                audit.audit(world)


if __name__ == "__main__":
    unittest.main()
