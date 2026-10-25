"""P2: preserve original World data during charmap/preproc before host ASM."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.grandworld_native.data_asm_staging import prepare, assemble, MANIFEST


@unittest.skipUnless(shutil.which("gcc"), "GNU C preprocessor/assembler required")
class OriginalGameDataStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = Path(self.tmp.name) / "world"
        self.output = Path(self.tmp.name) / "host"
        (self.world / "tools/preproc").mkdir(parents=True)
        (self.world / "data").mkdir()
        (self.world / "charmap.txt").write_text("A = 0x41\n", encoding="utf-8")
        fake_preproc = self.world / "tools/preproc/preproc"
        # Test-only passthrough: the real pipeline ALWAYS invokes the pinned
        # World preprocessor binary, not this minimal fixture.
        fake_preproc.write_text(
            '#!/bin/sh\nif [ "$1" = "-s" ]; then cat "$2"; else cat; fi\n',
            encoding="utf-8")
        fake_preproc.chmod(0o755)
        self.original = self.world / "data/original.s"
        self.assembly = (".section .rodata\n.byte 0xA5\n"
                         ".align 3\n.word 0x12345678\n")
        self.original.write_text(self.assembly, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_original_preprocessor_runs_before_abi_conversion(self):
        staged = prepare(self.world, self.output)
        self.assertEqual(staged["prepared"], 1)
        self.assertEqual(self.original.read_text(), self.assembly)
        compiled = assemble(self.world, self.output)
        self.assertEqual(compiled["native_objects"], 1)
        self.assertTrue((self.output / "original.o").is_file())
        self.assertEqual(self.original.read_text(), self.assembly)
        self.assertFalse(compiled["game_data_fabricated"])

    def test_preprocessed_celadon_operands_build_as_real_i386_object(self):
        # The first stage snapshots the unmodified game-data stream.
        # x86 GAS rejects these spaced original macro arguments unless the
        # three known expressions are normalized AFTER preprocessing.
        script = self.world / "data/event_scripts.s"
        original = (
            ".macro goto_if_ge lhs, threshold, target\n"
            "\t.4byte \\lhs\n"
            "\t.4byte \\threshold\n"
            "\t.4byte \\target\n"
            ".endm\n"
            ".set VAR_TEMP_1, 0x4000\n"
            ".set MAX_COINS, 9999\n"
            "\tgoto_if_ge VAR_TEMP_1, (MAX_COINS + 1) - 10, "
            "CeladonCity_GameCorner_EventScript_FisherNoRoomForCoins\n"
            "\tgoto_if_ge VAR_TEMP_1, (MAX_COINS + 1) - 20, "
            "CeladonCity_GameCorner_EventScript_ScientistNoRoomForCoins\n"
            "\tgoto_if_ge VAR_TEMP_1, (MAX_COINS + 1) - 20, "
            "CeladonCity_GameCorner_EventScript_GentlemanNoRoomForCoins\n"
        )
        script.write_text(original, encoding="utf-8")
        staged = prepare(self.world, self.output)
        self.assertEqual(staged["prepared"], 2)
        self.assertEqual(script.read_text(encoding="utf-8"), original)
        report = assemble(self.world, self.output)
        self.assertEqual(report["native_objects"], 2, report["results"])
        event = next(row for row in report["results"]
                     if row["source"] == "data/event_scripts.s")
        self.assertEqual(event["generated_asm_conversions"]["celadon_expression"], 3)
        self.assertTrue((self.output / "event_scripts.o").is_file())
        self.assertEqual(script.read_text(encoding="utf-8"), original)

    def test_cpp_expanded_celadon_game_scripts_compile_from_saved_stream(self):
        self.original.unlink()
        scripts = self.world / "data/event_scripts.s"
        original = (
            ".macro goto_if_ge variable, coins, target\n"
            "\t.4byte 0x12345678\n"
            ".endm\n"
            ".section .rodata\n"
            "\tgoto_if_ge VAR_TEMP_1, (9999 + 1) - 10, "
            "CeladonCity_GameCorner_EventScript_FisherNoRoomForCoins\n"
            "\tgoto_if_ge VAR_TEMP_1, (9999 + 1) - 20, "
            "CeladonCity_GameCorner_EventScript_ScientistNoRoomForCoins\n"
            "\tgoto_if_ge VAR_TEMP_1, (9999 + 1) - 20, "
            "CeladonCity_GameCorner_EventScript_GentlemanNoRoomForCoins\n"
        )
        scripts.write_text(original, encoding="utf-8")
        prepared = prepare(self.world, self.output)
        self.assertEqual(prepared["prepared"], 1)
        compiled = assemble(self.world, self.output)
        self.assertEqual(compiled["native_objects"], 1)
        self.assertEqual(compiled["results"][0]["generated_asm_conversions"]
                         ["celadon_expression"], 3)
        self.assertTrue((self.output / "event_scripts.o").is_file())
        self.assertEqual(scripts.read_text(encoding="utf-8"), original)

    def test_unexpected_preprocessed_celadon_count_fails_closed(self):
        self.original.unlink()
        scripts = self.world / "data/event_scripts.s"
        scripts.write_text(".section .rodata\n.byte 0x42\n", encoding="utf-8")
        prepare(self.world, self.output)
        with self.assertRaisesRegex(ValueError, "exactly three Celadon"):
            assemble(self.world, self.output)
        self.assertFalse((self.output / "event_scripts.o").exists())

    def test_tampering_with_staged_original_is_rejected(self):
        prepare(self.world, self.output)
        original = self.output / "_original_preproc/original.s"
        original.write_bytes(original.read_bytes() + b".byte 0\n")
        with self.assertRaises(ValueError):
            assemble(self.world, self.output)

    def test_manifest_path_traversal_is_rejected(self):
        prepare(self.world, self.output)
        path = self.output / MANIFEST
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["records"][0]["source"] = "data/../out.s"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError):
            assemble(self.world, self.output)


if __name__ == "__main__":
    unittest.main()
