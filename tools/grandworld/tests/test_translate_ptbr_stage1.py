"""PT-BR patch tests: all anchor files, glyphs, placeholders, and no write on drift."""
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

SRC = Path(__file__).resolve().parents[1] / "translate_ptbr_stage1.py"
spec = importlib.util.spec_from_file_location("grandworld_ptbr", SRC)
pt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pt)


class PortugueseStage1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
        strings = []
        for rows in pt.C_SECTIONS.values():
            for old, new in rows.values():
                strings.append(new)
        for rows in pt.ASM_SECTIONS.values():
            for parts in rows.values():
                strings += parts
        charset = set()
        for part in strings:
            part = re.sub(r"\{[^{}]+\}", "", part)
            part = re.sub(r"\\[npl]", "", part)
            charset.update(part)
        charset.discard("\n")
        charset.discard("\r")
        charset.difference_update(pt.CUSTOM_CHARACTER_MAP)
        # The test charmap represents ONLY the glyphs that the translations use.
        self.charmap = self.root / "charmap.txt"
        self.charmap.write_text(
            "".join(f"'{letter}' = {idx % 240:02X}\n" for idx, letter in
                    enumerate(sorted(charset)) if letter not in ('"', "'", "\\")) +
            "@ Hiragana\n", encoding="utf-8")
        self.original = {}
        for relative, entries in pt.C_SECTIONS.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "".join(f'const u8 {symbol}[] = _("' + old + '");\n'
                        for symbol, (old, _new) in entries.items()),
                encoding="utf-8")
            self.original[relative] = path.read_bytes()
        for relative, entries in pt.ASM_SECTIONS.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            blocks = []
            for label, parts in entries.items():
                required = "".join(sorted(pt.TOKEN.findall("".join(parts))))
                # Synthetic upstream dialogue with the same symbolic variables.
                blocks.append(label + '::\n\t.string "' + required + ' original.$"\n\n')
            path.write_text("".join(blocks), encoding="utf-8")
            self.original[relative] = path.read_bytes()

    def test_dry_run_does_not_modify_files(self):
        result = pt.run(self.root)
        self.assertEqual(result["mode"], "preflight")
        self.assertGreater(result["translation_entries"], 75)
        for name, previous in self.original.items():
            self.assertEqual((self.root / name).read_bytes(), previous)

    def test_all_files_apply_and_are_ptbr(self):
        result = pt.run(self.root, write=True)
        self.assertEqual(result["mode"], "applied")
        self.assertFalse(result["save_format_modified"])
        self.assertFalse(result["accent_tilde_font_complete"])
        self.assertEqual(set(result["by_file"]), set(pt.C_SECTIONS) | set(pt.ASM_SECTIONS))
        self.assertIn("Novo Jogo", (self.root / "src/main_menu.c").read_text())
        self.assertIn("Comprar", (self.root / "src/strings.c").read_text())
        self.assertIn("Quer salvar o jogo?", (self.root / "data/text/save.inc").read_text())
        self.assertIn("{PLAYER}{KUN}", (self.root / "data/text/birch_speech.inc").read_text())
        for name in self.original:
            self.assertNotEqual((self.root / name).read_bytes(), self.original[name])
        with self.assertRaisesRegex(ValueError, "expected 1"):
            pt.run(self.root, write=True)

    def test_c_source_drift_rejects_atomically(self):
        file = self.root / "src/strings.c"
        file.write_text(file.read_text().replace("Search completed.", "changed upstream"))
        before = {n: (self.root / n).read_bytes() for n in self.original}
        with self.assertRaisesRegex(ValueError, "SearchCompleted"):
            pt.run(self.root, write=True)
        for name, original in before.items():
            self.assertEqual((self.root / name).read_bytes(), original)

    def test_asm_source_drift_rejects_atomically(self):
        file = self.root / "data/text/save.inc"
        file.write_text(file.read_text().replace("gText_ConfirmSave::", "WRONG_LABEL::"))
        before = {n: (self.root / n).read_bytes() for n in self.original}
        with self.assertRaisesRegex(ValueError, "gText_ConfirmSave"):
            pt.run(self.root, write=True)
        for name, previous in before.items():
            self.assertEqual((self.root / name).read_bytes(), previous)

    def test_game_variables_cannot_disappear(self):
        with self.assertRaisesRegex(ValueError, "placeholder changed"):
            pt.validate_translation(self.root, "{PLAYER} saved.", "Game saved.", "save")

    def test_unmapped_glyphs_fail(self):
        with self.assertRaisesRegex(ValueError, "unsupported PT-BR glyph"):
            pt.validate_glyphs(self.root, "coração")
        with self.assertRaisesRegex(ValueError, "unsupported PT-BR glyph"):
            pt.validate_glyphs(self.root, "não")

    def test_every_portuguese_entry_uses_plain_ascii(self):
        # The user explicitly requested no accents, cedilla or new font glyphs.
        self.assertEqual(pt.plain_ptbr("Você não quer poções, ação e evolução?"),
                         "Voce nao quer pocoes, acao e evolucao?")
        self.assertEqual(pt.plain_ptbr("POKéMON e POKéDEX"), "POKEMON e POKEDEX")
        for file, entries in pt.C_SECTIONS.items():
            for label, (old, translated) in entries.items():
                normalized = pt.plain_ptbr(translated)
                self.assertTrue(normalized.isascii(), (file, label))
                self.assertNotIn("ç", normalized)
                pt.validate_translation(self.root, old, normalized, label)
        for file, entries in pt.ASM_SECTIONS.items():
            for label, parts in entries.items():
                for part in parts:
                    self.assertTrue(pt.plain_ptbr(part).isascii(), (file, label))
        total = sum(len(x) for x in pt.C_SECTIONS.values()) + sum(
            len(x) for x in pt.ASM_SECTIONS.values())
        self.assertGreaterEqual(total, 1535)

    def test_dewford_dialogue_batch_present(self):
        town = pt.ASM_SECTIONS['data/maps/DewfordTown/scripts.inc']
        self.assertGreaterEqual(len(town), 23)
        self.assertIn('STEVEN', ''.join(town['Route104_Text_LandedInDewfordDeliverLetter']))
        self.assertIn('PETALBURG', ''.join(town['DewfordTown_Text_SetSailBackToPetalburg']))
        self.assertIn('{STR_VAR_1}', ''.join(town['DewfordTown_Text_YeahDefinitionOfInRightNow']))
        self.assertTrue(all(''.join(parts).endswith(chr(36)) for parts in town.values()))

    def test_coastal_routes_batch_present(self):
        route = pt.ASM_SECTIONS['data/maps/Route109/scripts.inc']
        self.assertEqual(len(route), 16)
        self.assertIn('STERN', ''.join(route['DewfordTown_Text_BrineyLandedInSlateportDeliverGoods']))
        self.assertIn('ROD', ''.join(pt.ASM_SECTIONS['data/maps/Route106/scripts.inc']['Route106_Text_TrainerTips']))

    def test_route_story_batches_present(self):
        expected = {
            "data/maps/Route110/scripts.inc": 43,
            "data/maps/Route111/scripts.inc": 30,
            "data/maps/Route112/scripts.inc": 8,
            "data/maps/Route102/scripts.inc": 7,
            "data/maps/Route103/scripts.inc": 11,
            "data/maps/Route104/scripts.inc": 32,
            "data/maps/Route30/scripts.inc": 22,
            "data/maps/Route31/scripts.inc": 17,
            "data/maps/Route32/scripts.inc": 43,
            "data/maps/Route113/scripts.inc": 6,
            "data/maps/Route114/scripts.inc": 6,
            "data/maps/Route115/scripts.inc": 3,
        }
        for relative, count in expected.items():
            with self.subTest(relative=relative):
                self.assertEqual(len(pt.ASM_SECTIONS[relative]), count)
        self.assertIn("{PLAYER}", "".join(
            pt.ASM_SECTIONS["data/maps/Route30/scripts.inc"][
                "Route30_Text_Elm_Disaster"]))

    def test_escape_typo_fails(self):
        with self.assertRaisesRegex(ValueError, "unknown text escape"):
            pt.validate_translation(self.root, r"Hello\n", r"Oi\z", "bad")


if __name__ == "__main__":
    unittest.main()
