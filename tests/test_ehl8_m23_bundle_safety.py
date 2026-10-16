"""M2.3 safe SHA-matched host start and real log-based lobby conditions."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import emerald_qa_lab as L
import emerald_qa_lobby as Lobby


class HostStartBundle(unittest.TestCase):
    def test_m23_opt_in_and_sha256_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            app = Path(td)
            game = app / "pokeemerald.exe"
            server = app / "EmeraldSessionServerM23.exe"
            game.write_bytes(b"m23-game")
            server.write_bytes(b"m23-server")
            marker = app / "EHL8_M23_GAME_MATCHED.txt"
            marker.write_text(json.dumps({
                "game_sha256": hashlib.sha256(game.read_bytes()).hexdigest(),
                "server_sha256": hashlib.sha256(server.read_bytes()).hexdigest(),
            }), encoding="utf-8")
            cmd = L.server_command(app, 45680, admin=True)
            self.assertEqual(cmd[0], str(server))
            self.assertIn("--resume-v1", cmd)
            self.assertIn("--host-start", cmd)
            self.assertIn("--admin-stdin", cmd)
            self.assertNotIn("--host-start", L.server_command(app, 45680, admin=False))
            server.write_bytes(b"tampered")
            with self.assertRaises(RuntimeError):
                L.server_command(app, 45680, admin=True)

    def test_lobby_ready_and_started_from_real_log_format(self):
        self.assertEqual(Lobby.latest_ready_count("EHL8_READY_COUNT=0/2\nEHL8_READY_COUNT=2/2"), 2)
        self.assertEqual(Lobby.latest_ready_count("EHL8_READY_COUNT=1/2"), 1)
        self.assertIsNone(Lobby.latest_ready_count("EHL8_READY_COUNT=3/2"))
        self.assertFalse(Lobby.latest_room_started("EHL8_ROOM_STARTED=0"))
        self.assertTrue(Lobby.latest_room_started("EHL8_ROOM_STARTED=0\nEHL8_ROOM_STARTED=1"))
        self.assertIsNone(Lobby.latest_room_started("EHL8_ROOM_COUNT=2/2"))
