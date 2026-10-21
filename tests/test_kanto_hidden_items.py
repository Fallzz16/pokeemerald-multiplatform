"""Synthetic persistent-flag and geometry tests for Kanto hidden items."""
from pathlib import Path
import sys
import json
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"kanto"))
from import_exteriors import import_kanto_hidden_items


class HiddenItems(unittest.TestCase):
    def fixtures(self, item="ITEM_POTION"):
        context=tempfile.TemporaryDirectory()
        root=Path(context.name)
        f=root/"fire"/"data/maps/Route1/map.json"
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps({"bg_events":[{
            "type":"hidden_item","x":9,"y":11,"elevation":0,
            "item":item,"flag":"FLAG_HIDDEN_ITEM_ROUTE1_POTION",
            "quantity":1,"underfoot":False
        }]}),encoding="utf-8")
        e=root/"emerald"/"data/maps/Kanto_Route1/map.json"
        e.parent.mkdir(parents=True)
        e.write_text(json.dumps({"bg_events":[],"object_events":[]}),encoding="utf-8")
        flags=root/"emerald/include/constants/flags.h"
        flags.parent.mkdir(parents=True)
        flags.write_text(
            "#define FLAG_UNUSED_0x264 0x264\n"
            "#define FLAG_UNUSED_0x265 0x265\n"
            "#define FLAG_KANTO_ITEM_000 FLAG_UNUSED_0x264\n"
            "#endif // GUARD_CONSTANTS_FLAGS_H\n",encoding="utf-8")
        items=root/"emerald/include/constants/items.h"
        items.write_text("#define ITEM_POTION 10\n",encoding="utf-8")
        return context,root/"fire",root/"emerald",e,flags

    def test_appends_persistent_non_colliding_hidden_flag(self):
        ctx,f,e,map_path,flags=self.fixtures()
        with ctx:
            report=import_kanto_hidden_items(
                f,e,["Route1"],[{"flag_value":0x264}])
            self.assertEqual(report["total"],1)
            self.assertEqual(report["items"][0]["flag_value"],0x265)
            obj=json.loads(map_path.read_text())["bg_events"][0]
            self.assertEqual(obj["flag"],"FLAG_KANTO_HIDDEN_000")
            self.assertEqual((obj["x"],obj["y"],obj["item"]),(9,11,"ITEM_POTION"))
            self.assertIn("#define FLAG_KANTO_ITEM_000",flags.read_text())
            self.assertIn("#define FLAG_KANTO_HIDDEN_000",flags.read_text())

    def test_unknown_item_rejected(self):
        ctx,f,e,map_path,flags=self.fixtures(item="ITEM_NOT_AVAILABLE")
        with ctx, self.assertRaisesRegex(RuntimeError,"unavailable"):
            import_kanto_hidden_items(f,e,["Route1"],[{"flag_value":0x264}])


if __name__=="__main__":
    unittest.main()
