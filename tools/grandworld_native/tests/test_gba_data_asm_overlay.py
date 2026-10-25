"""Native GAS compatibility must preserve original byte-width semantics."""
import tempfile
import unittest
from pathlib import Path
import shutil
import subprocess

from tools.grandworld_native.gba_data_asm_overlay import scan, transform_text


class GbaAssemblySyntaxTests(unittest.TestCase):
    def test_arm_align_and_word_have_correct_i386_width(self):
        original = '\t.align 3\n\t.word ScriptPointer\n\t.2byte 123\n'
        normalized, changed = transform_text(original)
        self.assertEqual(normalized,
                         '\t.p2align 3\n\t.4byte ScriptPointer\n\t.2byte 123\n')
        self.assertEqual(changed["align"], 1)
        self.assertEqual(changed["word"], 1)

    def test_celadon_macro_expressions_not_content_modified(self):
        text = '\n'.join(
            '\tgoto_if_ge VAR_TEMP_1, (MAX_COINS + 1) - 10, '
            'CeladonCity_GameCorner_EventScript_FisherNoRoomForCoins'
            for _ in range(3)) + '\n'
        normalized, count = transform_text(text, True)
        self.assertEqual(count["celadon_expression"], 3)
        self.assertEqual(normalized.count('(MAX_COINS+1)-10'), 3)
        self.assertEqual(normalized.count('goto_if_ge'), 3)

    def test_comments_and_quotes_do_not_corrupt_data(self):
        source = ('\t.string "abc @ keep"\n'
                  '\t.4byte gSpriteRef  @ human-readable comment\n'
                  '\t@ GBA-only comment\n'
                  '\t.section .rodata,"a",@progbits\n')
        normalized, counts = transform_text(source)
        self.assertIn('"abc @ keep"', normalized)
        self.assertIn('.4byte gSpriteRef  # human-readable comment', normalized)
        self.assertIn('# GBA-only comment', normalized)
        self.assertIn('@progbits', normalized)
        self.assertEqual(counts["arm_comment"], 2)

    def test_unspaced_arm_comments_and_elf_type_metadata(self):
        original = (
            "\t@Custom battle tower command\n"
            "\tspecial ChooseHalfPartyForBattle @choose three\n"
            "\t.type some_function, @function\n"
            "\t.section .rodata, @progbits\n"
            "\t.4byte PointerRef\n"
        )
        transformed, changes = transform_text(original)
        self.assertIn("#Custom battle tower command", transformed)
        self.assertIn("#choose three", transformed)
        self.assertIn("@function", transformed)
        self.assertIn("@progbits", transformed)
        self.assertEqual(changes["arm_comment"], 2)
        self.assertEqual(transformed.splitlines(), [
            "\t#Custom battle tower command",
            "\tspecial ChooseHalfPartyForBattle #choose three",
            "\t.type some_function, @function",
            "\t.section .rodata, @progbits",
            "\t.4byte PointerRef",
        ])

    def test_apply_is_dry_run_by_default_and_fails_on_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src/main.c").write_text("", encoding="utf-8")
            path = root / "data/maps/CeladonCity_GameCorner_Frlg/scripts.inc"
            path.parent.mkdir(parents=True)
            source = (
                '\tgoto_if_ge VAR_TEMP_1, (MAX_COINS + 1) - 10, '
                'CeladonCity_GameCorner_EventScript_Any\n') * 3
            path.write_text(source, encoding="utf-8")
            dry = scan(root, False)
            self.assertFalse(dry["applied_to_disposable_source"])
            self.assertEqual(path.read_text(), source)
            applied = scan(root, True)
            self.assertTrue(applied["applied_to_disposable_source"])
            self.assertIn('(MAX_COINS+1)-10', path.read_text())
            with self.assertRaises(ValueError):
                scan(root, False)

    @unittest.skipUnless(shutil.which("gcc") and shutil.which("objcopy"),
                         "native GNU assembler and binutils required")
    def test_gba_word_width_and_alignment_in_real_i386_object(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asm = root / "data.s"
            obj = root / "data.o"
            raw = root / "data.bin"
            source = (".section .rodata\n"
                      ".byte 0xA5\n"
                      "\t.align 3\n"
                      "gOriginalPointer:\n"
                      "\t.word 0x12345678\n")
            normalized, counts = transform_text(source)
            self.assertEqual(counts["align"], 1)
            self.assertEqual(counts["word"], 1)
            asm.write_text(normalized, encoding="utf-8")
            subprocess.run(["gcc", "-m32", "-c", str(asm), "-o", str(obj)],
                           check=True, capture_output=True)
            subprocess.run(["objcopy", "--dump-section", ".rodata=" + str(raw),
                            str(obj)], check=True, capture_output=True)
            payload = raw.read_bytes()
            self.assertEqual(len(payload), 12)
            self.assertEqual(payload[0], 0xA5)
            self.assertEqual(payload[1:8], bytes(7))
            self.assertEqual(payload[8:], bytes.fromhex("78563412"))

    def test_unexpected_celadon_script_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src/main.c").write_text("", encoding="utf-8")
            script = root / "data/maps/CeladonCity_GameCorner_Frlg/scripts.inc"
            script.parent.mkdir(parents=True)
            script.write_text('goto_if_ge 1,2,3\n')
            with self.assertRaises(ValueError):
                scan(root, True)


if __name__ == "__main__":
    unittest.main()
