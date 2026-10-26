"""Independent in-game trade source audit for unresolved 12 grass-only species."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

FILE=Path(__file__).resolve().parents[1]/"audit_grass_trade_leads.py"
sp=importlib.util.spec_from_file_location("tradesource",FILE)
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)


class TradeSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.wild=self.root/"wild.json"
        self.trade=self.root/"trades.h"
        maps=[{"map":f"MAP_ROUTE{n}"} for n in range(301)]
        maps[0]["land_mons"]={"encounter_rate":10,"mons":[{"species":"SPECIES_BAGON"}]}
        self.wild.write_text(json.dumps({"wild_encounter_groups":[
            {"label":"gWildMonHeaders","for_maps":True,"encounters":maps}]}))
        self.source="""static const struct InGameTrade sIngameTrades[] =
{
    [INGAME_TRADE_HORSEA] =
    {
        .species = SPECIES_HORSEA,
        .nickname = _("SEASOR"),
        .requestedSpecies = SPECIES_BAGON
    },
    [INGAME_TRADE_RATTATA] =
    {
        .species = SPECIES_RATTATA,
        .requestedSpecies = SPECIES_LAPRAS
    }
};
"""
        self.trade.write_text(self.source)

    def test_explicit_given_species_not_requested_species(self):
        a=m.inspect(self.wild,self.trade,min_trades=2)
        self.assertEqual(a["trade_entries_parsed"],2)
        self.assertEqual(a["trade_lead_species"],1)
        self.assertEqual(a["leads"][0]["offers"],"SPECIES_HORSEA")
        self.assertEqual(a["leads"][0]["requires"],"SPECIES_BAGON")
        self.assertTrue(a["leads"][0]["requested_species_in_original_land_table"])
        self.assertFalse(a["trade_gameplay_verified"])

    def test_requested_species_outside_grass_not_approved(self):
        self.wild.write_text(self.wild.read_text().replace("SPECIES_BAGON","SPECIES_PIDGEY"))
        r=m.inspect(self.wild,self.trade,min_trades=2)
        self.assertFalse(r["leads"][0]["requested_species_in_original_land_table"])
        self.assertFalse(r["source_scans_can_prove_obtainability"])

    def test_excludes_unrelated_species_and_requested_lapras(self):
        r=m.inspect(self.wild,self.trade,min_trades=2)
        self.assertEqual([x["offers"] for x in r["leads"]],["SPECIES_HORSEA"])

    def test_no_false_lead_from_comments(self):
        self.trade.write_text(self.source.replace(
            ".species = SPECIES_HORSEA,", ".species = SPECIES_PIDGEY,\n // .species = SPECIES_HORSEA,"))
        self.assertEqual(m.inspect(self.wild,self.trade,min_trades=2)["trade_lead_species"],0)

    def test_incomplete_trades_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"incomplete World in-game trades"):
            m.inspect(self.wild,self.trade)

    def test_incomplete_land_tables_fail_closed(self):
        self.wild.write_text(json.dumps({"wild_encounter_groups":[]}))
        with self.assertRaisesRegex(ValueError,"incomplete pinned World"):
            m.inspect(self.wild,self.trade,min_trades=2)

    def test_no_mutation_and_not_final_release(self):
        a=self.wild.read_bytes();b=self.trade.read_bytes()
        r=m.inspect(self.wild,self.trade,min_trades=2)
        self.assertFalse(r["rom_modified"])
        self.assertFalse(r["saves_modified"])
        self.assertFalse(r["release_approved"])
        self.assertEqual(a,self.wild.read_bytes())
        self.assertEqual(b,self.trade.read_bytes())


if __name__=="__main__":
    unittest.main()
