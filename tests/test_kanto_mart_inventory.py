"""Check fail-closed original FireRed shop-stock conversion."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"kanto"))
from import_exteriors import render_firered_mart_stock


class MartInventoryTests(unittest.TestCase):
    def fixtures(self, raw):
        temp=tempfile.TemporaryDirectory()
        root=Path(temp.name)
        src=root/"fire"/"data"/"maps"/"TestCity_Mart"
        src.mkdir(parents=True)
        (src/"scripts.inc").write_text(raw,encoding="utf-8")
        items=root/"emerald"/"include"/"constants"
        items.mkdir(parents=True)
        (items/"items.h").write_text(
            "#define ITEM_POKE_BALL 1\n#define ITEM_POTION 2\n",encoding="utf-8")
        return temp,root/"fire",root/"emerald"

    def test_preserves_exact_order(self):
        t,a,b=self.fixtures("TestCity_Mart_Items::\n\t.2byte ITEM_POKE_BALL\n\t.2byte ITEM_POTION\n\t.2byte ITEM_NONE\n")
        with t:
            data=render_firered_mart_stock(a,b,"TestCity_Mart","Kanto_Test_Items")
            self.assertEqual([x.split()[-1] for x in data.splitlines()
                              if ".short" in x],["ITEM_POKE_BALL","ITEM_POTION"])
            self.assertIn("Kanto_Test_Items:",data)
            self.assertIn("pokemartlistend",data)
            self.assertNotIn("ITEM_NONE",data)

    def test_unavailable_item_blocks_conversion(self):
        t,a,b=self.fixtures("TestCity_Mart_Items::\n.2byte ITEM_UNAVAILABLE\n.2byte ITEM_NONE\n")
        with t,self.assertRaisesRegex(RuntimeError,"Unavailable"):
            render_firered_mart_stock(a,b,"TestCity_Mart","Kanto_Test_Items")

    def test_missing_terminator_blocks_conversion(self):
        t,a,b=self.fixtures("TestCity_Mart_Items::\n.2byte ITEM_POTION\n")
        with t,self.assertRaisesRegex(RuntimeError,"Unterminated"):
            render_firered_mart_stock(a,b,"TestCity_Mart","Kanto_Test_Items")

    def test_duplicate_item_blocks_conversion(self):
        t,a,b=self.fixtures("TestCity_Mart_Items::\n.2byte ITEM_POTION\n.2byte ITEM_POTION\n.2byte ITEM_NONE\n")
        with t,self.assertRaisesRegex(RuntimeError,"duplicate"):
            render_firered_mart_stock(a,b,"TestCity_Mart","Kanto_Test_Items")


if __name__=="__main__":
    unittest.main()
