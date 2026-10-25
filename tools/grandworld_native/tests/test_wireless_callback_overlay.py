import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.grandworld_native.wireless_callback_overlay import ORIGINAL, HOST, transform


class WirelessCallbackTests(unittest.TestCase):
    def test_native_only_callbacks_preserve_original_arm_bodies(self):
        source = "/* pinned GBA source */\n" + ORIGINAL
        after = transform(source)
        self.assertIn("#if defined(GW_WORLD_NATIVE)", after)
        self.assertIn("#else\n" + ORIGINAL + "#endif", after)
        self.assertEqual(after.count('asm("bx r2")'), 1)
        self.assertEqual(after.count('asm("bx r1")'), 1)
        self.assertEqual(after.count('asm("bx r0")'), 1)

    def test_refuses_drift_and_double_apply(self):
        source = ORIGINAL
        with self.assertRaises(ValueError):
            transform(source.replace('asm("bx r2")', 'asm("bx r3")'))
        with self.assertRaises(ValueError):
            transform(transform(source))

    @unittest.skipUnless(shutil.which("gcc"), "host GCC required")
    def test_host_callbacks_forward_arguments_without_arm_instructions(self):
        callback_source = (
            "#include <stddef.h>\n"
            "typedef unsigned short u16;\n"
            + HOST +
            "static int total;\n"
            "static void master(int request, int error) { total += request * 10 + error; }\n"
            "static void slave(u16 request) { total += request; }\n"
            "static void identify(void) { ++total; }\n"
            "int main(void) {\n"
            "    Callback_Dummy_M(7, 3, master);\n"
            "    Callback_Dummy_S(5, slave);\n"
            "    Callback_Dummy_ID(identify);\n"
            "    Callback_Dummy_ID(NULL);\n"
            "    return total == 79 ? 0 : 1;\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            program = Path(tmp) / "rfu.c"
            binary = Path(tmp) / "rfu-test"
            program.write_text(callback_source, encoding="utf-8")
            result = subprocess.run(
                ["gcc", "-std=gnu17", "-DGW_WORLD_NATIVE=1", "-Wall",
                 "-Werror=implicit-function-declaration",
                 str(program), "-o", str(binary)],
                capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            executed = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(executed.returncode, 0, executed.stderr)


if __name__ == "__main__":
    unittest.main()
