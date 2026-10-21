"""Source item ball conversion, flags, and fail-closed tests."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "kanto"))
from import_exteriors import import_kanto_visible_items


class KantoOriginalItemsTests(unittest.TestCase):
    def test_item_is_persistent_and_does_not_mutate_hoenn(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            src=root/"firered"
            em=root/"emerald"
            (src/"data/scripts").mkdir(parents=True)
            (src/"data/scripts/item_ball_scripts.inc").write_text(
                "Route1_EventScript_ItemPotion::\n"
                "    finditem ITEM_POTION\n    end\n",
                encoding="utf-8",
            )
            source_map=src/"data/maps/Route1/map.json"
            source_map.parent.mkdir(parents=True)
            source_map.write_text(json.dumps({
                "object_events":[{"graphics_id":"OBJ_EVENT_GFX_ITEM_BALL",
                    "x":3,"y":4,"elevation":3,
                    "script":"Route1_EventScript_ItemPotion",
                    "flag":"FLAG_HIDE_SOURCE_POTION"}]
            }),encoding="utf-8")
            target_map=em/"data/maps/Kanto_Route1/map.json"
            target_map.parent.mkdir(parents=True)
            target_map.write_text(json.dumps({
                "object_events":[], "warp_events":[],
                "id":"MAP_KANTO_ROUTE1"}),encoding="utf-8")
            (em/"data/maps/Kanto_Route1/scripts.inc").write_text(
                "Kanto_Route1_MapScripts::\n    .byte 0\n",encoding="utf-8")
            flags=em/"include/constants/flags.h"
            flags.parent.mkdir(parents=True)
            flags.write_text(
                "#define FLAG_UNUSED_0x264 0x264\n"
                "#define FLAG_UNUSED_0x265 0x265\n"
                "#endif // GUARD_CONSTANTS_FLAGS_H\n",encoding="utf-8")
            items=em/"include/constants/items.h"
            items.write_text("#define ITEM_POTION 13\n",encoding="utf-8")
            before=source_map.read_bytes()
            result=import_kanto_visible_items(src, em, ["Route1"], minimum=1)
            self.assertEqual(result["total"],1)
            self.assertEqual(result["items"][0]["flag_value"],0x264)
            self.assertEqual(before,source_map.read_bytes())
            output=json.loads(target_map.read_text())
            self.assertEqual(output["object_events"][0]["flag"],"FLAG_KANTO_ITEM_000")
            self.assertIn("finditem ITEM_POTION",
                          (em/"data/maps/Kanto_Route1/scripts.inc").read_text())
            self.assertIn("#define FLAG_KANTO_ITEM_000",
                          flags.read_text())
            with self.assertRaisesRegex(RuntimeError,"already installed|header changed"):
                import_kanto_visible_items(src, em, ["Route1"], minimum=1)

    def test_unknown_source_item_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            src=root/"fr"
            em=root/"em"
            (src/"data/scripts").mkdir(parents=True)
            (src/"data/scripts/item_ball_scripts.inc").write_text(
                "Route1_EventScript_ItemBad::\n"
                "    finditem ITEM_NOT_IN_EMERALD\n    end\n",encoding="utf-8")
            (src/"data/maps/Route1").mkdir(parents=True)
            (src/"data/maps/Route1/map.json").write_text(json.dumps({
                "object_events":[{"graphics_id":"OBJ_EVENT_GFX_ITEM_BALL",
                    "x":2,"y":4,"elevation":0,
                    "script":"Route1_EventScript_ItemBad"}]}))
            (em/"data/maps/Kanto_Route1").mkdir(parents=True)
            (em/"data/maps/Kanto_Route1/map.json").write_text(
                json.dumps({"object_events":[]}))
            (em/"data/maps/Kanto_Route1/scripts.inc").write_text("")
            (em/"include/constants").mkdir(parents=True)
            (em/"include/constants/flags.h").write_text(
                "#define FLAG_UNUSED_0x264 0x264\n"
                "#endif // GUARD_CONSTANTS_FLAGS_H\n")
            (em/"include/constants/items.h").write_text("#define ITEM_POTION 13\n")
            with self.assertRaisesRegex(RuntimeError,"does not provide"):
                import_kanto_visible_items(src,em,["Route1"],minimum=1)


if __name__ == "__main__":
    unittest.main()
