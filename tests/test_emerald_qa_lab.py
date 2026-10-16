"""QA laboratory tests; never invokes the real game or modifies real saves."""
import importlib.util
import io
import json
import socket
from pathlib import Path
from unittest.mock import patch
import shutil
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools" / "emerald_qa_lab.py"
spec = importlib.util.spec_from_file_location("emerald_qa_lab", MODULE)
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)


class LabTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.app = self.base / "app"
        self.app.mkdir()
        for name in ("pokeemerald.exe", "SDL2.dll", "emerald_profilectl.exe", "EmeraldSessionServer.exe"):
            (self.app / name).write_bytes(b"fake")
        self.root = self.base / "testing"

    def fake_profilectl(self, cmd, **kw):
        self.assertEqual(kw["cwd"], str(self.app))
        self.assertNotIn("--session-pin", " ".join(cmd))
        action, root, profile = cmd[1:4]
        dest = Path(root) / profile
        if action in ("new", "import"):
            dest.mkdir()
            if action == "new":
                (dest / "pokeemerald.sav").write_bytes(b"\xff" * 131072)
            else:
                shutil.copyfile(cmd[4], dest / "pokeemerald.sav")
        elif action == "backup":
            (dest / "backups").mkdir(exist_ok=True)
            shutil.copyfile(dest / "pokeemerald.sav", dest / "backups" / "000001.sav")
        return subprocess.CompletedProcess(cmd, 0, "ok", "")

    def test_command_contract_and_local_only_pin_not_argv(self):
        self.assertIn("--profile-id=QA_A", L.game_command(self.app, "p", "QA_A", "ehl8", 45680))
        self.assertIn("--session-pin-stdin", L.game_command(self.app, "p", "QA_B", "ehl8", 45680))
        self.assertEqual(L.server_command(self.app, 45680)[2], "127.0.0.1")
        self.assertIn("--pin-stdin", L.server_command(self.app, 45680))
        self.assertNotIn("--session-pin-stdin", L.game_command(self.app, "p", "QA_A", "offline", 45680))
        with self.assertRaises(ValueError):
            L.game_command(self.app, "p", "../escape", "ehl8", 45680)
        for port in (0, 65535, "bad"):
            with self.assertRaises(ValueError):
                L.validate_port(port)
        for pin in ("123", "12345x", "1234567"):
            with self.assertRaises(ValueError):
                L.validate_pin(pin)

    def test_unique_profiles_and_source_integrity(self):
        save = self.base / "owned.sav"
        save.write_bytes(b"TRAINER A" * 800)
        original = save.read_bytes()
        with patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            session = L.prepare_session(self.app, self.root, (save, None), "ehl8")
        self.assertEqual(save.read_bytes(), original)
        self.assertEqual((session / "profiles/QA_A/pokeemerald.sav").read_bytes(), original)
        self.assertEqual((session / "profiles/QA_B/pokeemerald.sav").stat().st_size, 131072)
        self.assertNotEqual(session / "profiles/QA_A", session / "profiles/QA_B")
        marker = json.loads((session / L.MARKER).read_text())
        self.assertEqual(marker["source_sha256"][0], L.file_digest(save))
        self.assertIsNone(marker["source_sha256"][1])
        self.assertFalse((self.root / "profiles").exists())
        with patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            second = L.prepare_session(self.app, self.root, (None, None), "offline")
        self.assertNotEqual(session, second)
        self.assertTrue((session / "profiles/QA_A/pokeemerald.sav").exists())

    def test_invalid_assets_and_invalid_source_fail_before_creating_session(self):
        (self.app / "SDL2.dll").unlink()
        with self.assertRaises(FileNotFoundError):
            L.prepare_session(self.app, self.root)
        self.assertFalse(self.root.exists())
        (self.app / "SDL2.dll").write_bytes(b"fake")
        with self.assertRaises(FileNotFoundError):
            L.prepare_session(self.app, self.root, ("missing.sav", None))
        self.assertFalse(self.root.exists())

    def test_cleanup_is_scoped_only_to_marked_session(self):
        with patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            session = L.prepare_session(self.app, self.root)
        production = self.base / "my_real_profile"
        production.mkdir()
        (production / "pokeemerald.sav").write_bytes(b"REAL")
        with self.assertRaises(ValueError):
            L.remove_session(production, self.root)
        with self.assertRaises(ValueError):
            L.remove_session(self.root, self.root)
        self.assertEqual((production / "pokeemerald.sav").read_bytes(), b"REAL")
        L.remove_session(session, self.root)
        self.assertFalse(session.exists())
        self.assertEqual((production / "pokeemerald.sav").read_bytes(), b"REAL")

    def test_launch_two_real_process_commands_with_mocked_windows_processes(self):
        class FakeProcess:
            def __init__(self):
                self.code = None
                self.stdin = io.BytesIO()
            def poll(self):
                return self.code
            def terminate(self):
                self.code = 143

        launched = []
        def fake_popen(cmd, **kw):
            launched.append((cmd, kw))
            return FakeProcess()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, "run", side_effect=self.fake_profilectl), \
             patch.object(L.subprocess, "Popen", side_effect=fake_popen):
            session = manager.launch("ehl8", (None, None), port, "123456")
        self.assertEqual(len(launched), 3)
        self.assertIn("--bind", launched[0][0])
        self.assertIn("127.0.0.1", launched[0][0])
        self.assertIn("--profile-id=QA_A", launched[1][0])
        self.assertIn("--profile-id=QA_B", launched[2][0])
        for cmd, _ in launched:
            self.assertNotIn("123456", " ".join(cmd))
        self.assertEqual(manager.session, session)
        self.assertTrue(manager.running())
        for process in manager.games:
            process.code = 0
        with patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            manager.complete()
        self.assertTrue(manager.backups_done)
        self.assertTrue((session / "report.json").is_file())

    def test_conflicting_ehl8_port_fails_without_creating_test_saves(self):
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen(1)
            port = occupied.getsockname()[1]
            manager = L.QASession(self.app, self.root)
            with self.assertRaises(RuntimeError):
                manager.launch("ehl8", port=port, pin="123456")
            self.assertFalse(self.root.exists())

    def test_complete_never_backs_up_while_any_game_is_running(self):
        with patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            session = L.prepare_session(self.app, self.root)
        manager = L.QASession(self.app, self.root)
        manager.session = session
        manager.games = [type("P", (), {"poll": lambda self: None})(),
                         type("P", (), {"poll": lambda self: 0})()]
        with patch.object(L.subprocess, "run", side_effect=AssertionError("premature backup")):
            manager.complete()
        self.assertFalse(manager.backups_done)
        manager.games = [type("P", (), {"poll": lambda self: 0})(),
                         type("P", (), {"poll": lambda self: 0})()]
        with patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            manager.complete()
        self.assertTrue(manager.backups_done)
        for pid in L.PROFILE_IDS:
            self.assertTrue((session / "profiles" / pid / "backups" / "000001.sav").is_file())
        report = json.loads((session / "report.json").read_text())
        self.assertEqual(report["exit_codes"], [0, 0])
        self.assertEqual(len(report["backups"]), 2)


if __name__ == "__main__":
    unittest.main()


class BotsIntegrationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.app = self.base / 'app'
        self.app.mkdir()
        (self.app / 'EmeraldSessionServer.exe').write_bytes(b'mock')
        (self.app / 'EmeraldQABots.exe').write_bytes(b'mock')
        self.root = self.base / 'isolated'

    def test_bot_mode_does_not_create_saves_and_cleanup_is_scoped(self):
        from unittest.mock import patch
        class FakeProcess:
            def __init__(self):
                self.returncode = None
                self.stdin = io.BytesIO()
            def poll(self): return self.returncode
            def terminate(self): self.returncode = 143
        processes = []
        def popen(cmd, **kw):
            self.assertNotIn('123456', ' '.join(cmd))
            obj = FakeProcess()
            processes.append(obj)
            return obj
        bot = launcher = L.QABotSession(self.app, self.root)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        with patch.object(L.subprocess, 'Popen', side_effect=popen):
            session = bot.launch(port, '123456')
        self.assertEqual(len(processes), 2)
        self.assertFalse(list(session.rglob('*.sav')))
        self.assertNotIn('123456', str((session / L.MARKER).read_text()))
        bot.bot.returncode = 0
        (session / 'bots-report.json').write_text(json.dumps({
            'rounds_passed': 25, 'rounds_requested': 25, 'identities_attempted': 50}))
        self.assertIn('25/25', bot.complete())
        self.assertEqual(bot.server.poll(), 143)
        L.remove_session(session, self.root)
        self.assertFalse(session.exists())
        self.assertFalse((self.root / 'profiles').exists())

    def test_missing_bot_does_not_allocate_session(self):
        (self.app / 'EmeraldQABots.exe').unlink()
        with self.assertRaises(FileNotFoundError):
            L.QABotSession(self.app, self.root).launch(45680, '123456')
        self.assertFalse(self.root.exists())


class ReopenSingleSavedTrainerTests(unittest.TestCase):
    """Regression: reopen a prior session *alone*, without a second game/save."""
    setUp = LabTests.setUp
    fake_profilectl = LabTests.fake_profilectl
    def _session(self):
        with patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            return L.prepare_session(self.app, self.root, (None, None), "ehl8")

    def test_discovery_excludes_bots_and_bad_marker(self):
        self.assertEqual(L.saved_game_sessions(self.root), [])
        existing = self._session()
        bots = L.create_bot_session(self.root)
        self.assertEqual(L.saved_game_sessions(self.root), [existing])
        with self.assertRaises(ValueError):
            L.existing_session(self.root, bots, "QA_A")
        marker = existing / L.MARKER
        original = marker.read_bytes()
        marker.write_text('bad-json', encoding='utf-8')
        self.assertEqual(L.saved_game_sessions(self.root), [])
        marker.write_bytes(original)
        self.assertEqual(L.saved_game_sessions(self.root), [existing])

    def test_reopen_only_a_uses_existing_save_and_preserves_original_report(self):
        session = self._session()
        a = session / 'profiles' / 'QA_A' / 'pokeemerald.sav'
        b = session / 'profiles' / 'QA_B' / 'pokeemerald.sav'
        # Valid-size byte patterns are QA stand-ins, not distributable save games.
        a.write_bytes(b'A'*131072)
        b.write_bytes(b'B'*131072)
        original_a, original_b = a.read_bytes(), b.read_bytes()
        (session / 'report.json').write_text('{"original":true}', encoding='utf-8')

        class FakeProcess:
            def __init__(self): self.code = None
            def poll(self): return self.code
        seen=[]
        def popen(argv, **kw):
            seen.append((argv,kw))
            return FakeProcess()
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, 'Popen', side_effect=popen):
            self.assertEqual(manager.reopen_single(session, 'QA_A'), session)
        self.assertEqual(len(seen), 1)
        self.assertIn('--profile-id=QA_A', seen[0][0]); self.assertNotIn('--profile-id=QA_B', seen[0][0])
        self.assertNotIn('--session-client', ' '.join(seen[0][0]))
        self.assertFalse(any('EmeraldSessionServer.exe' in x for x in seen[0][0]))
        self.assertEqual(a.read_bytes(),original_a)
        self.assertEqual(b.read_bytes(),original_b)
        self.assertTrue(manager.running())
        with self.assertRaises(RuntimeError):
            manager.reopen_single(session,'QA_B')
        manager.games[0].code=0
        with patch.object(L.subprocess, 'run', side_effect=self.fake_profilectl) as calls:
            manager.complete()
        self.assertEqual(calls.call_count,1)
        self.assertEqual(calls.call_args.args[0][-1], 'QA_A')
        report=json.loads((session/manager.report_name).read_text())
        self.assertEqual(report['profiles'],['QA_A'])
        self.assertEqual(report['exit_codes'],[0])
        self.assertEqual((session/'report.json').read_text(),'{"original":true}')
        self.assertEqual(a.read_bytes(),original_a)
        self.assertEqual(b.read_bytes(),original_b)
        self.assertTrue((session/'profiles'/'QA_A'/'backups'/'000001.sav').is_file())
        self.assertFalse((session/'profiles'/'QA_B'/'backups').exists())

        # A new Lab process can rediscover and reopen the same session later.
        later=L.QASession(self.app,self.root)
        with patch.object(L.subprocess, 'Popen', side_effect=popen):
            later.reopen_single(L.saved_game_sessions(self.root)[0], 'QA_B')
        self.assertEqual(len(seen),2)
        self.assertIn('--profile-id=QA_B', seen[-1][0])
        self.assertNotEqual(manager.report_name, later.report_name)

    def test_reopen_rejects_redirected_save_and_arbitrary_path(self):
        session=self._session()
        outside=self.base/'real'
        outside.mkdir(); (outside/'pokeemerald.sav').write_bytes(b'private')
        with self.assertRaises(ValueError):
            L.existing_session(self.root, outside, 'QA_A')
        with self.assertRaises(ValueError):
            L.existing_session(self.root, session, '../../escape')
        a=session/'profiles'/'QA_A'/'pokeemerald.sav'
        a.unlink()
        try:
            a.symlink_to(outside/'pokeemerald.sav')
        except (OSError, NotImplementedError):
            self.skipTest('symlink privilege unavailable on Windows runner')
        with self.assertRaises(ValueError):
            L.existing_session(self.root, session, 'QA_A')
        self.assertEqual((outside/'pokeemerald.sav').read_bytes(),b'private')

    def test_good_trainer_remains_listed_if_companion_save_is_missing(self):
        session = self._session()
        (session / 'profiles' / 'QA_B' / 'pokeemerald.sav').unlink()
        self.assertIn(session, L.saved_game_sessions(self.root))
        L.existing_session(self.root, session, 'QA_A')
        with self.assertRaises(ValueError):
            L.existing_session(self.root, session, 'QA_B')

    def test_reopen_rejects_redirected_logs_before_mutating_manager(self):
        session = self._session()
        logs = session / 'logs'
        shutil.rmtree(logs)
        manager = L.QASession(self.app, self.root)
        with self.assertRaises(ValueError):
            manager.reopen_single(session, 'QA_A')
        self.assertIsNone(manager.session)
        self.assertEqual(manager.games, [])

    def test_bot_only_session_cannot_reopen_as_game(self):
        bot=L.create_bot_session(self.root)
        manager=L.QASession(self.app,self.root)
        with self.assertRaises(ValueError):
            manager.reopen_single(bot,'QA_A')
        self.assertFalse(list(bot.rglob('*.sav')))

class M21AdminPipeTests(unittest.TestCase):
    def test_admin_companion_is_selected_without_replacing_legacy(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "EmeraldSessionServer.exe").touch()
            self.assertNotIn("--admin-stdin", L.server_command(folder, 45680, admin=True))
            (folder / "EmeraldSessionServerM21.exe").touch()
            self.assertIn("--admin-stdin", L.server_command(folder, 45680, admin=True))
            self.assertNotIn("--admin-stdin", L.server_command(folder, 45680, admin=False))

    def test_private_pipe_allowlist_and_no_leaked_pin(self):
        class Fake:
            def __init__(self):
                self.stdin = io.BytesIO()
                self.returncode = None
            def poll(self):
                return self.returncode
        with tempfile.TemporaryDirectory() as temp:
            manager = L.QASession(temp, temp)
            manager.mode = "ehl8"
            manager.admin_enabled = True
            manager.server = Fake()
            self.assertEqual(manager.admin_command("lock"), "LOCK ON")
            self.assertEqual(manager.admin_command("kick", "QA_B"), "KICK QA_B")
            self.assertEqual(manager.admin_command("unlock"), "LOCK OFF")
            self.assertEqual(manager.server.stdin.getvalue(), b"LOCK ON\nKICK QA_B\nLOCK OFF\n")
            for action, profile in (("kick", "BAD"), ("lock", "QA_A"), ("reset", None)):
                with self.assertRaises(ValueError):
                    manager.admin_command(action, profile)
            manager.admin_enabled = False
            with self.assertRaises(RuntimeError):
                manager.admin_command("lock")
