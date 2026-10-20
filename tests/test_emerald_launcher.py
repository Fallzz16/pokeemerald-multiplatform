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
    def test_pin_handoff_succeeds_without_logging_or_persisting_pin(self):
        from unittest.mock import Mock
        child = Mock()
        child.stdin = Mock()
        launcher.deliver_pin_or_terminate(child, "123456")
        child.stdin.write.assert_called_once_with(b"123456\n")
        child.stdin.flush.assert_called_once_with()
        child.stdin.close.assert_called_once_with()
        child.terminate.assert_not_called()

    def test_pin_handoff_broken_pipe_terminates_untracked_child(self):
        from unittest.mock import Mock
        child = Mock()
        child.poll.return_value = None
        child.stdin.write.side_effect = BrokenPipeError("closed stdin")
        with self.assertRaises(OSError) as error:
            launcher.deliver_pin_or_terminate(child, "123456")
        self.assertNotIn("123456", str(error.exception))
        child.terminate.assert_called_once_with()
        child.wait.assert_called_once_with(timeout=3)
        child.stdin.close.assert_called_once_with()

    def test_pin_handoff_timeout_escalates_to_kill(self):
        import subprocess
        from unittest.mock import Mock
        child = Mock()
        child.poll.return_value = None
        child.stdin.flush.side_effect = BrokenPipeError("flushing closed stdin")
        child.wait.side_effect = [subprocess.TimeoutExpired("game", 3), 0]
        with self.assertRaises(OSError):
            launcher.deliver_pin_or_terminate(child, "123456")
        child.terminate.assert_called_once()
        child.kill.assert_called_once()
        self.assertEqual(child.wait.call_count, 2)
        child.stdin.close.assert_called_once()

    def test_ehl8_host_launch_plan_requires_matched_game_and_server(self):
        import hashlib
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            game = home / "pokeemerald.exe"
            server = home / "EmeraldSessionServerM23.exe"
            game.write_bytes(b"game-test-only")
            server.write_bytes(b"server-test-only")
            manifest = home / "EHL8_M23_GAME_MATCHED.txt"
            manifest.write_text(json.dumps({
                "game_sha256": hashlib.sha256(game.read_bytes()).hexdigest(),
                "server_sha256": hashlib.sha256(server.read_bytes()).hexdigest(),
            }), encoding="utf-8")
            command, manual = launcher.server_launch_plan(home, game, 45680)
            self.assertTrue(manual)
            self.assertEqual(Path(command[0]), server)
            self.assertIn("--host-start", command)
            self.assertIn("--admin-stdin", command)
            self.assertIn("--resume-v1", command)
            self.assertNotIn("123456", " ".join(command))
            server.write_bytes(b"incompatible-server")
            with self.assertRaisesRegex(ValueError, "não verificado"):
                launcher.server_launch_plan(home, game, 45680)
            # An invalid marker must never silently fall back to old server.
            (home / "EmeraldSessionServer.exe").touch()
            with self.assertRaises(ValueError):
                launcher.server_launch_plan(home, game, 45680)

    def test_legacy_ehl8_host_plan_preserves_autostart(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "EmeraldSessionServer.exe").touch()
            command, manual = launcher.server_launch_plan(home, home / "pokeemerald.exe", 45680)
            self.assertFalse(manual)
            self.assertNotIn("--host-start", command)
            self.assertNotIn("--admin-stdin", command)

    def test_live_lobby_gate_requires_two_real_ready_players(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "room.log"
            self.assertIsNone(launcher.read_lobby_gate(log))
            log.write_text("EHL8_ROOM_COUNT=0/2\n"
                           "EHL8_READY_COUNT=0/2\n"
                           "EHL8_ROOM_STARTED=0\n"
                           "EHL8_ROOM_COUNT=1/2\n"
                           "EHL8_READY_COUNT=1/2\n", encoding="utf-8")
            self.assertEqual(launcher.read_lobby_gate(log), {
                "players": 1, "ready": 1, "started": False})
            with log.open("a", encoding="utf-8") as out:
                out.write("EHL8_ROOM_COUNT=2/2\nEHL8_READY_COUNT=2/2\n")
            self.assertEqual(launcher.read_lobby_gate(log), {
                "players": 2, "ready": 2, "started": False})
            with log.open("a", encoding="utf-8") as out:
                out.write("EHL8_ROOM_STARTED=1\n")
            self.assertTrue(launcher.read_lobby_gate(log)["started"])

    def test_admin_start_writes_exact_local_command(self):
        from unittest.mock import Mock
        process = Mock()
        process.poll.return_value = None
        process.stdin.closed = False
        launcher.send_lobby_admin(process, "START")
        process.stdin.write.assert_called_once_with(b"START\n")
        process.stdin.flush.assert_called_once_with()
        with self.assertRaises(ValueError):
            launcher.send_lobby_admin(process, "KICK QA_B")
        with self.assertRaises(ValueError):
            launcher.send_lobby_admin(process, "START\nKICK QA_B")
        self.assertEqual(process.stdin.write.call_count, 1)

    def test_pin_handoff_keeps_private_pipe_for_manual_start(self):
        from unittest.mock import Mock
        child = Mock()
        child.stdin.closed = False
        child.poll.return_value = None
        launcher.deliver_pin_or_terminate(child, "123456", keep_open=True)
        child.stdin.write.assert_called_once_with(b"123456\n")
        child.stdin.close.assert_not_called()
        launcher.send_lobby_admin(child, "START")
        child.stdin.write.assert_any_call(b"START\n")

    def test_tcp_preflight_with_a_real_local_socket(self):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            self.assertTrue(launcher.test_tcp_reachability("127.0.0.1", port))
            accepted, _ = listener.accept()
            accepted.close()

    def test_tcp_preflight_does_not_assume_online_gameplay(self):
        from unittest.mock import patch
        with patch.object(launcher.socket, "create_connection",
                          side_effect=ConnectionRefusedError("closed")):
            with self.assertRaises(ConnectionRefusedError):
                launcher.test_tcp_reachability("100.101.102.103", "45680")
        with self.assertRaises(ValueError):
            launcher.test_tcp_reachability("0.0.0.0", "45680")
        with self.assertRaises(ValueError):
            launcher.test_tcp_reachability("127.0.0.1", "45680", timeout=0)

    def test_dedicated_session_requires_six_digit_pin_and_valid_ipv4(self):
        args = launcher.make_command("pokeemerald.exe","profiles","trainer",
                                     "dedicated","127.0.0.1","45680","123456")
        self.assertIn("--session-client=127.0.0.1:45680",args)
        self.assertIn("--session-pin-stdin",args)
        self.assertIn("--session-wait-for-start",args)
        self.assertNotIn("--session-wait-for-start",
                         launcher.make_command("pokeemerald.exe","profiles","trainer","offline"))
        self.assertFalse(any("123456" in value for value in args))
        self.assertNotIn("--lan-client=127.0.0.1:45680",args)
        for bad in ("","123","abcdef","1234567"):
            with self.assertRaises(ValueError):
                launcher.make_command("pokeemerald.exe","profiles","trainer",
                                      "dedicated","127.0.0.1","45680",bad)
        with self.assertRaises(ValueError):
            launcher.make_command("pokeemerald.exe","profiles","trainer",
                                  "dedicated","not-a-host","45680","123456")

    def test_real_dedicated_room_count_from_bounded_server_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            log=Path(tmp)/"server.log"
            self.assertIsNone(launcher.read_room_occupancy(log))
            log.write_text("INFO EHL8_ROOM_COUNT=0/2\n"
                           "INFO EHL8_ROOM_COUNT=1/2\n"
                           "INFO unrelated log\n",encoding="utf-8")
            self.assertEqual(launcher.read_room_occupancy(log),(1,2))
            with log.open("a",encoding="utf-8") as out:
                out.write("ignored line\n"*1000)
                out.write("INFO EHL8_ROOM_COUNT=2/2\n")
            self.assertEqual(launcher.read_room_occupancy(log),(2,2))
            log.write_text("INFO EHL8_ROOM_COUNT=2/1\n",encoding="utf-8")
            self.assertIsNone(launcher.read_room_occupancy(log))

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

    def test_preview_installer_uses_its_own_local_save_directory(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            here=Path(tmp)/"release"
            here.mkdir()
            (here/"EHL8_PREVIEW_MODE.txt").write_text("preview",encoding="utf-8")
            with mock.patch.object(launcher,"application_dir",return_value=here), \
                 mock.patch.dict("os.environ",{"LOCALAPPDATA":tmp}):
                preview=launcher.profile_root()
                self.assertEqual(preview,Path(tmp)/"EmeraldHybridEHL8Preview"/"profiles")
                (here/"PORTABLE_MODE.txt").touch()
                self.assertEqual(launcher.profile_root(),here/"profiles")
                self.assertNotEqual(preview,Path(tmp)/"EmeraldHybrid"/"profiles")

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
