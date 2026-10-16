"""M2.1-A: QA lobby protocol-log viewer tests, no live game or saves."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "tools" / "emerald_qa_lobby.py"
spec = importlib.util.spec_from_file_location("emerald_qa_lobby", SOURCE)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class Process:
    def __init__(self, code=None):
        self.code = code
    def poll(self):
        return self.code


class Session:
    def __init__(self, directory):
        self.session = directory
        self.mode = "ehl8"
        self.server = Process()
        self.games = [Process(), Process()]


class LobbyTest(unittest.TestCase):
    def test_protocol_parsing(self):
        self.assertEqual(M.latest_room("EHL8_ROOM_COUNT=0/2\nEHL8_ROOM_COUNT=2/2"), (2, 2))
        self.assertIsNone(M.latest_room("EHL8_ROOM_COUNT=50/2"))
        self.assertIsNone(M.latest_room("EHL8_ROOM_COUNT=2/4"))
        self.assertIsNone(M.latest_room("No lobby"))
        self.assertEqual(M.latest_client_state("[EHL8] session state=4\n[EHL8] session state=5"), "EM JOGO")
        self.assertEqual(M.latest_client_state("[EHL8] session state=6"), "ERRO DE CONEXÃO")

    def test_lobby_transition_and_no_stale_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            logs = d / "logs"
            logs.mkdir()
            (logs / "servidor.log").write_text("EHL8_ROOM_COUNT=2/2\n")
            for pid in ("QA_A", "QA_B"):
                (logs / (pid + "-rede.log")).write_text("[EHL8] session state=5\n")
            manager = Session(d)
            state = M.lobby_snapshot(manager)
            self.assertEqual(state["room"], "2/2")
            self.assertEqual(state["players"], {"QA_A": "EM JOGO", "QA_B": "EM JOGO"})
            manager.games[1].code = 0
            (logs / "servidor.log").write_text("EHL8_ROOM_COUNT=1/2\n")
            self.assertEqual(M.lobby_snapshot(manager)["room"], "1/2")
            self.assertEqual(M.lobby_snapshot(manager)["players"]["QA_B"], "FECHADO")
            manager.server.code = 1
            self.assertEqual(M.lobby_snapshot(manager)["room"], "ENCERRADA")
            self.assertEqual(M.lobby_snapshot(manager)["players"]["QA_A"], "SEM SERVIDOR")

    def test_offline_and_bounded_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            manager = Session(d)
            manager.mode = "offline"
            self.assertEqual(M.lobby_snapshot(manager)["room"], "SEM SESSÃO EHL8")
            src = d / "huge.log"
            src.write_text("X" * 20000 + "\nEHL8_ROOM_COUNT=2/2\n")
            self.assertLessEqual(len(M.tail_text(src).encode("utf-8")), 8192)
            self.assertEqual(M.latest_room(M.tail_text(src)), (2, 2))
            self.assertEqual(M.tail_text(d / "missing.log"), "")
            symlink = d / "link.log"
            try:
                symlink.symlink_to(src)
            except (OSError, NotImplementedError):
                pass
            else:
                self.assertEqual(M.tail_text(symlink), "")

if __name__ == "__main__":
    unittest.main()


class M21AdminStatusTests(unittest.TestCase):
    def test_latest_lock_event_is_authoritative(self):
        self.assertIsNone(M.latest_room_lock("EHL8_ROOM_COUNT=2/2"))
        self.assertTrue(M.latest_room_lock("EHL8_ROOM_LOCKED=0\nEHL8_ROOM_LOCKED=1\n"))
        self.assertFalse(M.latest_room_lock("EHL8_ROOM_LOCKED=1\nEHL8_ROOM_LOCKED=0\n"))

    def test_admin_disabled_on_server_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "logs").mkdir()
            (root / "logs" / "servidor.log").write_text("EHL8_ROOM_COUNT=2/2\nEHL8_ROOM_LOCKED=1\n")
            session = Session(root)
            session.admin_enabled = True
            current = M.lobby_snapshot(session)
            self.assertTrue(current["admin"])
            self.assertTrue(current["locked"])
            session.server.code = 0
            ended = M.lobby_snapshot(session)
            self.assertFalse(ended["admin"])
            self.assertIsNone(ended["locked"])
