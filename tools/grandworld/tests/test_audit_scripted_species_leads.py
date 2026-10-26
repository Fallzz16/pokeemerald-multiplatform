"""New focused source-only script event inventory tests (no gameplay retests)."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

path=Path(__file__).resolve().parents[1]/"audit_scripted_species_leads.py"
spec=importlib.util.spec_from_file_location("speciesleads",path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ScriptLeadsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"maps"
        self.root.mkdir()
        self.silph=self.root/"SilphCo_7F_Frlg"
        self.silph.mkdir()
        (self.silph/"scripts.inc").write_text(
            "SilphCo_7F_EventScript_LaprasGuy::\n"
            "  givemon SPECIES_LAPRAS, 25\n"
            "  # givemon SPECIES_CLAMPERL, 12\n"
            "  bufferspeciesname STR_VAR_1, SPECIES_HORSEA\n")
        self.cave=self.root/"UnionCave_B2F"
        self.cave.mkdir()
        (self.cave/"scripts.inc").write_text(
            "  setwildbattle SPECIES_LAPRAS, 20\n"
            "  dowildbattle\n  giveegg SPECIES_FINNEON\n")

    def test_lapras_has_two_scripted_leads(self):
        r=mod.inspect(self.root,min_files=2)
        lapras=next(x for x in r["species"] if x["species"]=="SPECIES_LAPRAS")
        self.assertEqual({x["op"] for x in lapras["declarations"]},{"givemon","setwildbattle"})
        self.assertFalse(lapras["event_accessibility_verified"])
        self.assertFalse(r["species_obtainability_certified"])

    def test_other_declaration_kinds(self):
        r=mod.inspect(self.root,min_files=2)
        finneon=next(x for x in r["species"] if x["species"]=="SPECIES_FINNEON")
        self.assertTrue(finneon["has_direct_script_declaration"])
        self.assertEqual(finneon["declarations"][0]["kind"],"scripted_egg_declaration")

    def test_comments_mentions_and_buffer_names_do_not_count(self):
        r=mod.inspect(self.root,min_files=2)
        for name in ("SPECIES_CLAMPERL","SPECIES_HORSEA"):
            row=next(x for x in r["species"] if x["species"]==name)
            self.assertFalse(row["has_direct_script_declaration"])

    def test_cannot_scan_nonexistent_map_folder(self):
        with self.assertRaisesRegex(ValueError,"missing World"):
            mod.inspect(self.root/"missing",min_files=2)

    def test_cannot_approve_truncated_source_scope(self):
        with self.assertRaisesRegex(ValueError,"too few World"):
            mod.inspect(self.root,min_files=3)

    def test_files_have_evidence_hashes_and_line_numbers(self):
        r=mod.inspect(self.root,min_files=2)
        self.assertEqual(r["map_script_files_scanned"],2)
        lapras=next(x for x in r["species"] if x["species"]=="SPECIES_LAPRAS")
        self.assertEqual(sorted(x["line"] for x in lapras["declarations"]),[1,2])
        self.assertTrue(all(len(x)==64 for x in r["matched_script_sha256"].values()))

    def test_unverified_gameplay_flags_remain_false(self):
        r=mod.inspect(self.root,min_files=2)
        self.assertEqual(r["original_residual_no_grass_or_evolution_path"],13)
        self.assertFalse(r["conditional_compilation_resolved"])
        self.assertFalse(r["dynamic_script_calls_and_trade_tables_analyzed"])
        self.assertFalse(r["release_approved"])


if __name__=="__main__":
    unittest.main()
