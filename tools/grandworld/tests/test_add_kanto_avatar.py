"""Ensure Red/Leaf graphics map only engine-supported FRLG poses."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "avatars", Path(__file__).resolve().parents[1] / "add_kanto_avatar.py")
avatars = importlib.util.module_from_spec(spec)
spec.loader.exec_module(avatars)

OLD = ("""    // Region merge: the player is Brendan/May in every region now (Kanto no longer uses
    // the FRLG Red/Leaf overworld sprites; Red's sprites are reused for the Johto rival).
    return sPlayerAvatarGfxIds[state][gender];""")
RELOAD = "            return table[gPlayerAvatar.gender][i].graphicsId;"


class FrlgPoseTests(unittest.TestCase):
    def test_red_leaf_poses_and_fallback(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "src").mkdir()
            (root / "src/field_player_avatar.c").write_text(OLD + "\n" + RELOAD)
            (root / "src/palette_swap.c").write_text(
                "    u16 val = VarGet(VAR_PLAYER_PALETTE);")
            avatar, palette = avatars.patch(root)
            for suffix in ("NORMAL", "BIKE", "SURF", "FIELD_MOVE", "FISH", "VS_SEEKER"):
                with self.subTest(suffix=suffix):
                    self.assertIn("OBJ_EVENT_GFX_RED_" + suffix, avatar)
                    self.assertIn("OBJ_EVENT_GFX_GREEN_" + suffix, avatar)
            self.assertNotIn("OBJ_EVENT_GFX_RED_ACRO", avatar)
            self.assertNotIn("OBJ_EVENT_GFX_GREEN_UNDERWATER", avatar)
            self.assertIn("return sPlayerAvatarGfxIds[state][gender];", avatar)
            self.assertIn("GetPlayerAvatarGraphicsIdByStateIdAndGender", avatar)
            self.assertIn("hero == 2 || hero == 3", palette)

    def test_rejects_unsupported_upstream_drift(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "src").mkdir()
            (root / "src/field_player_avatar.c").write_text("new unexpected source")
            (root / "src/palette_swap.c").write_text(
                "    u16 val = VarGet(VAR_PLAYER_PALETTE);")
            with self.assertRaisesRegex(ValueError, "source drift"):
                avatars.patch(root)


if __name__ == "__main__":
    unittest.main()
