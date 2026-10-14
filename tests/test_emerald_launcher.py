import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools" / "emerald_launcher.py"
spec = importlib.util.spec_from_file_location("emerald_launcher", MODULE)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

class GraphicalLauncherTests(unittest.TestCase):
    def test_modes(self):
        self.assertEqual(launcher.make_command("game.exe","profiles","user_1","offline")[-1], "--profile-id=user_1")
        self.assertEqual(launcher.make_command("game.exe","profiles","user_1","host")[-1], "--lan-host=45680")
        self.assertEqual(launcher.make_command("game.exe","profiles","user_1","join","100.101.102.103")[-1],
                         "--lan-client=100.101.102.103:45680")
        with self.assertRaises(ValueError):
            launcher.make_command("game.exe","profiles","user_1","dedicated")
        with self.assertRaises(ValueError):
            launcher.make_command("game.exe","profiles","../bad","offline")
    def test_invalid_network(self):
        for port in ("0","65535","abc","1.5"):
            with self.assertRaises(ValueError): launcher.validate_port(port)
        for ip in ("google.com","999.0.0.1","0.0.0.0","255.255.255.255","224.0.0.1"):
            with self.assertRaises(ValueError): launcher.validate_ipv4(ip)
        self.assertEqual(launcher.validate_port("65534"), 65534)
    def test_local_identity_does_not_modify_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"profile_example"
            folder.mkdir()
            original=b"save-test-only"+bytes(range(100))
            (folder/"pokeemerald.sav").write_bytes(original)
            launcher.write_nickname(folder,"Treinador")
            self.assertEqual((folder/"pokeemerald.sav").read_bytes(),original)
            self.assertEqual(launcher.find_profiles(Path(tmp)),[("profile_example","Treinador")])
            self.assertEqual(json.loads((folder/"profile.json").read_text())["nickname"],"Treinador")
    def test_names_and_missing_profile(self):
        self.assertEqual(launcher.validate_nickname("  May  "),"May")
        for name in ("", "x"*19, "\n"):
            with self.assertRaises(ValueError): launcher.validate_nickname(name)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(launcher.find_profiles(Path(tmp)/"not-created"),[])

    def test_launcher_preferences_remember_last_profile_and_preserve_sav(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"profiles"
            root.mkdir()
            profile=root/"trainer"
            profile.mkdir()
            before=b"not-a-real-save-test"+bytes(range(110))
            (profile/"pokeemerald.sav").write_bytes(before)
            launcher.write_settings(root,"trainer",False,"100.101.102.103","45680")
            got=launcher.read_settings(root)
            self.assertEqual(got["selected_profile"],"trainer")
            self.assertFalse(got["diagnostics"])
            self.assertEqual(got["last_port"],"45680")
            launcher.write_settings(root,"trainer",True,"127.0.0.1","45681")
            self.assertTrue(launcher.read_settings(root)["diagnostics"])
            self.assertEqual((profile/"pokeemerald.sav").read_bytes(),before)

    def test_corrupt_and_excessive_preferences_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"profiles"
            root.mkdir()
            path=launcher.settings_path(root)
            path.write_text("{broken",encoding="utf-8")
            self.assertEqual(launcher.read_settings(root),{})
            path.write_text("x"*40000,encoding="utf-8")
            self.assertEqual(launcher.read_settings(root),{})

    def test_log_not_inside_save_and_no_command_injection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"profiles"
            command=launcher.make_command("pokeemerald.exe",root,"trainer","host")
            self.assertIn("--profile-id=trainer",command)
            self.assertNotIn(";", "".join(command))
            with self.assertRaises(ValueError):
                launcher.make_command("pokeemerald.exe",root,"../trainer","host")

if __name__ == "__main__": unittest.main(verbosity=2)
