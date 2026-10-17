"""M2.3-A host-first lobby regression: no game until explicit user action."""
import io
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import importlib.util
import sys

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import emerald_qa_lab as L
import emerald_qa_lobby as Lobby


class FakeProcess:
    def __init__(self):
        self.code = None
        self.stdin = io.BytesIO()
    def poll(self):
        return self.code
    def terminate(self):
        self.code = 143
    def wait(self, timeout=None):
        return self.code
    def kill(self):
        self.code = 137


class ServerFirst(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.app = self.folder / "app"
        self.app.mkdir()
        self.root = self.folder / "testing"
        for file in ("pokeemerald.exe", "SDL2.dll",
                     "emerald_profilectl.exe", "EmeraldSessionServer.exe"):
            (self.app / file).write_bytes(b"fake")
        self.launched = []
        def fake_popen(argv, **kwargs):
            self.launched.append((argv, kwargs))
            return FakeProcess()
        self.popen = fake_popen
        self.port_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port_socket.bind(("127.0.0.1", 0))
        self.port = self.port_socket.getsockname()[1]
        self.port_socket.close()

    def fake_profilectl(self, argv, **kwargs):
        action, profile_root, pid = argv[1:4]
        target = Path(profile_root) / pid
        if action in ("import", "new"):
            target.mkdir()
            if action == "import":
                target.joinpath("pokeemerald.sav").write_bytes(Path(argv[4]).read_bytes())
            else:
                target.joinpath("pokeemerald.sav").write_bytes(b"\xff" * 131072)
        elif action == "backup":
            d = target / "backups"
            d.mkdir(exist_ok=True)
            d.joinpath("000001.sav").write_bytes(
                target.joinpath("pokeemerald.sav").read_bytes())
        return subprocess.CompletedProcess(argv, 0, "", "")

    def test_server_only_creates_lobby_0_of_2_without_game(self):
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, "Popen", side_effect=self.popen), \
             patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            folder = manager.start_server_only((None, None), self.port, "123456")
        self.assertEqual(len(self.launched), 1)
        self.assertIn("--pin-stdin", self.launched[0][0])
        self.assertNotIn("123456", " ".join(self.launched[0][0]))
        self.assertEqual(manager.games, [])
        self.assertTrue(manager.running())
        self.assertTrue(folder.joinpath("logs", "servidor.log").exists())
        self.assertTrue(folder.joinpath("profiles", "QA_A", "pokeemerald.sav").exists())
        self.assertFalse(manager.backups_done)
        with patch.object(L.subprocess, "run", side_effect=AssertionError("no premature backup")):
            manager.complete()
        self.assertFalse(manager.backups_done)
        self.assertTrue(manager.server.poll() is None)
        # Server log is produced by a real child; with the mock we emulate its
        # readiness lines, never pretend live TCP was tested here.
        folder.joinpath("logs", "servidor.log").write_text(
            "EHL8_ROOM_COUNT=0/2\nEHL8_READY_COUNT=0/2\n"
            "EHL8_ROOM_STARTED=0\nEHL8_ROOM_LOCKED=0\n", encoding="utf-8")
        snap = Lobby.lobby_snapshot(manager)
        self.assertEqual(snap["room"], "0/2")
        self.assertEqual(snap["ready"], 0)
        self.assertFalse(snap["started"])
        self.assertEqual(snap["players"]["QA_A"], "NÃO INICIADO")
        self.assertEqual(snap["players"]["QA_B"], "NÃO INICIADO")

    def test_launch_attaches_to_running_server_without_second_server(self):
        original_save = self.folder / "source.sav"
        original_save.write_bytes(b"A" * 131072)
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, "Popen", side_effect=self.popen), \
             patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            folder = manager.start_server_only((original_save, None), self.port, "123456")
            self.assertEqual(len(self.launched), 1)
            self.assertEqual(manager.launch("ehl8", (None, None), self.port, "123456"), folder)
            self.assertEqual(len(self.launched), 3)
            self.assertEqual(manager.session, folder)
            self.assertEqual([L.PROFILE_IDS[0], L.PROFILE_IDS[1]],
                             [c[0][2].split("=", 1)[1] for c in self.launched[1:]])
            self.assertEqual(original_save.read_bytes(), b"A" * 131072)
            self.assertEqual(folder.joinpath("profiles","QA_A","pokeemerald.sav").read_bytes(),
                             original_save.read_bytes())
            self.assertTrue(all(p.poll() is None for p in manager.games))
            for p in manager.games: p.code = 0
            manager.complete()
            self.assertTrue(manager.backups_done)
            self.assertEqual(len(manager.backup_status), 2)
        self.assertEqual(json.loads((folder / "report.json").read_text())["exit_codes"], [0, 0])
        self.assertTrue(all("--session-pin-stdin" in cmd for cmd, _ in self.launched[1:]))

    def test_join_one_at_a_time_then_start_remaining_without_extra_server(self):
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, "Popen", side_effect=self.popen), \
             patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            folder = manager.start_server_only(port=self.port, pin="123456")
            self.assertEqual(len(self.launched), 1)
            manager.launch_single("QA_A", self.port, "123456")
            self.assertEqual(manager.game_profiles, ["QA_A"])
            self.assertEqual(len(self.launched), 2)
            with self.assertRaises(RuntimeError):
                manager.launch_single("QA_A", self.port, "123456")
            manager.launch_single("QA_B", self.port, "123456")
            self.assertEqual(manager.game_profiles, ["QA_A", "QA_B"])
            self.assertEqual(len(self.launched), 3)
            self.assertEqual(manager.session, folder)
            with self.assertRaises(RuntimeError):
                manager.launch_games(self.port, "123456")
            self.assertEqual(len(self.launched), 3)

    def test_open_two_fills_missing_player_only(self):
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, "Popen", side_effect=self.popen), \
             patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            manager.start_server_only(port=self.port, pin="123456")
            manager.launch_single("QA_B", self.port, "123456")
            manager.launch_games(self.port, "123456")
            self.assertEqual(manager.game_profiles, ["QA_B", "QA_A"])
            self.assertEqual(len(self.launched), 3)
            for p in manager.games: p.code = 0
            manager.complete()
            report = json.loads((manager.session / "report.json").read_text())
            self.assertEqual(report["profiles"], ["QA_B", "QA_A"])

    def test_single_entry_checks_pin_port_and_live_server(self):
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, "Popen", side_effect=self.popen), \
             patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            manager.start_server_only(port=self.port, pin="123456")
            with self.assertRaises(ValueError):
                manager.launch_single("QA_A", self.port, "654321")
            with self.assertRaises(ValueError):
                manager.launch_single("QA_A", self.port+1, "123456")
            with self.assertRaises(ValueError):
                manager.launch_single("OTHER", self.port, "123456")
            self.assertEqual(len(self.launched), 1)
            manager.server.code = 1
            with self.assertRaises(RuntimeError):
                manager.launch_single("QA_A", self.port, "123456")

    def test_reopen_finished_qa_in_same_server(self):
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, "Popen", side_effect=self.popen), \
             patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            manager.start_server_only(port=self.port, pin="123456")
            manager.launch_single("QA_A", self.port, "123456")
            manager.games[0].code = 0
            manager.launch_single("QA_A", self.port, "123456")
            self.assertEqual(manager.game_profiles, ["QA_A"])
            self.assertEqual(len(self.launched), 3)
            manager.launch_games(self.port, "123456")
            self.assertEqual(manager.game_profiles, ["QA_A", "QA_B"])
            self.assertEqual(len(self.launched), 4)
            manager.stop()
            self.assertIsNotNone(manager.server.poll())

    def test_open_two_again_after_both_windows_closed_same_server(self):
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, "Popen", side_effect=self.popen), \
             patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            folder = manager.start_server_only(port=self.port, pin="123456")
            manager.launch("ehl8", port=self.port, pin="123456")
            self.assertEqual(len(self.launched), 3)
            for proc in manager.games:
                proc.code = 0
            self.assertTrue(manager.server.poll() is None)
            self.assertEqual(manager.launch("ehl8", port=self.port, pin="123456"), folder)
            self.assertEqual(len(self.launched), 5)
            self.assertEqual(manager.game_profiles, ["QA_A", "QA_B"])
            self.assertEqual(len(manager.games), 2)
            self.assertFalse(manager.backups_done)

    def test_failed_second_game_rolls_back_only_new_children(self):
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, "Popen", side_effect=self.popen), \
             patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            manager.start_server_only(port=self.port, pin="123456")
            original_send = manager._send_pin
            calls = [0]
            def fail_second(process, pin, keep_open=False):
                calls[0] += 1
                if calls[0] == 2:  # QA_A first, QA_B second
                    raise BrokenPipeError("simulated PIN pipe failure")
                return original_send(process, pin, keep_open=keep_open)
            with patch.object(manager, "_send_pin", side_effect=fail_second):
                with self.assertRaises(BrokenPipeError):
                    manager.launch_games(self.port, "123456")
            self.assertEqual(manager.game_profiles, [])
            self.assertEqual(manager.games, [])
            self.assertTrue(manager.server.poll() is None)
            self.assertEqual(len(self.launched), 3)
            self.assertEqual(self.launched[0][0][0], str(self.app / "EmeraldSessionServer.exe"))
            # The two newly launched games must not survive a failed PIN.
            # Popen is mocked; retain every fake process for lifecycle assertions.

    def test_wrong_port_or_pin_cannot_join_managed_server(self):
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, "Popen", side_effect=self.popen), \
             patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            manager.start_server_only(port=self.port, pin="123456")
            for bad_port, bad_pin in ((self.port, "654321"), (self.port + 1, "123456")):
                with self.assertRaises(ValueError):
                    manager.launch_games(port=bad_port, pin=bad_pin)
            self.assertEqual(len(self.launched), 1)
            self.assertEqual(manager.games, [])
            self.assertTrue(manager.running())
            with self.assertRaises(RuntimeError):
                manager.start_server_only(port=self.port, pin="123456")

    def test_offline_has_no_server_only_and_does_not_allocate(self):
        manager = L.QASession(self.app, self.root)
        with self.assertRaises(ValueError):
            manager.launch("offline", server_only=True)
        self.assertFalse(self.root.exists())
        with self.assertRaises(RuntimeError):
            manager.launch_games(port=self.port, pin="123456")
        self.assertFalse(self.root.exists())

    def test_terminated_server_must_not_receive_games(self):
        manager = L.QASession(self.app, self.root)
        with patch.object(L.subprocess, "Popen", side_effect=self.popen), \
             patch.object(L.subprocess, "run", side_effect=self.fake_profilectl):
            manager.start_server_only(port=self.port, pin="123456")
            manager.server.code = 1
            with self.assertRaises(RuntimeError):
                manager.launch_games(port=self.port, pin="123456")
            self.assertEqual(len(self.launched), 1)
            self.assertEqual(manager.games, [])


if __name__ == "__main__":
    unittest.main()
