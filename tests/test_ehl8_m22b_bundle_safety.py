"""Safety: only matched M2.2-B game/server binaries activate the new handshake."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import tempfile
import unittest
TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
MODULE = TOOLS / "emerald_qa_lab.py"
spec = importlib.util.spec_from_file_location("emerald_qa_lab_m22_test", MODULE)
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

class MatchedReconnectPreview(unittest.TestCase):
    def test_old_installs_keep_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=Path(tmp)
            (app / "EmeraldSessionServer.exe").write_bytes(b"old")
            (app / "EmeraldSessionServerM21.exe").write_bytes(b"old-m21")
            cmd=L.server_command(app,45680,admin=True)
            self.assertNotIn("--resume-v1",cmd)
            self.assertIn("--admin-stdin",cmd)

    def test_marker_checks_exact_binary_hashes_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=Path(tmp)
            game=app/"pokeemerald.exe"
            server=app/"EmeraldSessionServerM22.exe"
            marker=app/"EHL8_M22B_GAME_MATCHED.txt"
            game.write_bytes(b"game-test-binary")
            server.write_bytes(b"server-test-binary")
            marker.write_text(json.dumps({
                "game_sha256": hashlib.sha256(game.read_bytes()).hexdigest(),
                "server_sha256": hashlib.sha256(server.read_bytes()).hexdigest(),
                "source_commit": "same-commit-QA"}), encoding="utf-8")
            cmd=L.server_command(app,45680,admin=True)
            self.assertIn("--resume-v1",cmd)
            self.assertIn("--admin-stdin",cmd)
            self.assertEqual(cmd[0],str(server))
            self.assertNotIn("--resume-v1",L.server_command(app,45680,admin=False))
            game.write_bytes(b"other-game")
            with self.assertRaises(RuntimeError):
                L.server_command(app,45680,admin=True)

    def test_lobby_state_and_reservations(self):
        import emerald_qa_lobby as lobby
        self.assertEqual(lobby.latest_client_state("[EHL8] session state=7"),"RECONECTANDO (ATÉ 60s)")
        self.assertEqual(lobby.latest_reservations("EHL8_ROOM_RESERVED=1/2"),1)
        self.assertIsNone(lobby.latest_reservations("EHL8_ROOM_RESERVED=5/2"))
