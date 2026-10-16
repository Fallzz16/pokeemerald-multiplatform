"""Socket tests for protocol-only QA bot client; no Emerald game, no saves."""
from pathlib import Path
import importlib.util
import json
import socketserver
import struct
import threading
import tempfile
import time
import unittest
from unittest.mock import patch

p = Path(__file__).resolve().parents[1] / 'tools' / 'emerald_qa_bots.py'
spec = importlib.util.spec_from_file_location('emerald_qa_bots', p)
B = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = B
spec.loader.exec_module(B)


class Room:
    """Small EHL8-compatible socket fixture; not the real game/server."""
    def __init__(self, server):
        self.server = server
        self.players = {}
        self.in_game = False
        self.lock = threading.RLock()
        self.session = 12345678
        self.pin = b'123456'

    def send(self, sock, kind, payload=b''):
        with self.lock:
            sock.sendall(B.encode(B.Frame(kind, payload, self.session)))

    def broadcast(self, kind, payload=b'', exclude=None):
        with self.lock:
            for sock in list(self.players):
                if sock is not exclude:
                    try:
                        self.send(sock, kind, payload)
                    except OSError:
                        pass

    def snapshot(self):
        with self.lock:
            return bytes([len(self.players)])

    def remove(self, sock):
        with self.lock:
            slot = self.players.pop(sock, None)
            if slot is not None:
                self.broadcast(B.LEAVE, bytes([slot]))
            if not self.players:
                self.in_game = False


class FakePeer(socketserver.BaseRequestHandler):
    def handle(self):
        room = self.server.room
        stage = 'HELLO'
        sock = self.request
        try:
            while True:
                msg = B.receive(sock)
                if stage == 'HELLO':
                    if msg.kind != B.HELLO:
                        break
                    room.send(sock, B.WELCOME, b'\x02')
                    stage = 'AUTH'
                elif stage == 'AUTH':
                    if msg.kind != B.AUTH_PIN or msg.payload != room.pin:
                        room.send(sock, B.KICK, b'Invalid PIN')
                        break
                    room.send(sock, B.AUTH_PIN, b'\x01')
                    stage = 'JOIN'
                elif stage == 'JOIN':
                    if msg.kind != B.JOIN or len(room.players) >= 2:
                        room.send(sock, B.KICK, b'Lobby full')
                        break
                    with room.lock:
                        slot = next(x for x in (1, 2) if x not in room.players.values())
                        room.players[sock] = slot
                        stage = 'GAME' if room.in_game else 'LOBBY'
                        room.send(sock, B.JOIN, bytes([slot]))
                        room.broadcast(B.PLAYER_LIST, room.snapshot())
                        if room.in_game:
                            room.send(sock, B.START)
                elif msg.kind == B.READY:
                    if stage == 'LOBBY':
                        with room.lock:
                            room.ready.add(sock)
                            if len(room.players) == 2 and len(room.ready & room.players.keys()) == 2:
                                room.in_game = True
                                room.broadcast(B.START)
                                stage = 'GAME'
                elif msg.kind == B.POSE:
                    room.broadcast(B.POSE, bytes([room.players[sock]]) + msg.payload, exclude=sock)
                elif msg.kind == B.LEAVE:
                    break
                else:
                    break
        except (OSError, B.EHL8Error, EOFError, TimeoutError):
            pass
        finally:
            room.remove(sock)
            with room.lock:
                room.ready.discard(sock)


class ThreadServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self):
        super().__init__(('127.0.0.1', 0), FakePeer)
        self.room = Room(self)
        self.room.ready = set()


class BotTests(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadServer()
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.port = self.srv.server_address[1]

    def test_frame_layout_and_valid_lanp(self):
        b = B.encode(B.Frame(B.HELLO))
        self.assertEqual(len(b), 28)
        self.assertEqual(b[:4], b'EHL8')
        self.assertEqual(len(B.pose(1, 21, 22)), 18)
        self.assertEqual(B.pose(1, 21, 22)[:5], b'LANP\x01')
        with self.assertRaises(ValueError):
            B.pose(3, 4096, 100)

    def test_two_identity_pairs_and_protocol_movement(self):
        out = B.run_suite('127.0.0.1', self.port, '123456', cycles=3, timeout=2.0)
        self.assertEqual(out['identities_attempted'], 6)
        self.assertEqual(out['max_concurrent_clients'], 2)
        self.assertEqual(out['rounds_passed'], 3, out['errors'])
        self.assertEqual(out['rounds_failed'], 0)
        self.assertTrue(all(x['rejoin'] for x in out['rounds']))
        self.assertNotIn('pin', json.dumps(out).lower())

    def test_wrong_pin_does_not_pass(self):
        out = B.run_suite('127.0.0.1', self.port, '000000', cycles=1, timeout=1.0)
        self.assertEqual(out['rounds_passed'], 0)
        self.assertEqual(out['rounds_failed'], 1)
        self.assertNotIn('000000', json.dumps(out))

    def test_remote_host_not_allowed_and_count_bounded(self):
        with self.assertRaises(ValueError):
            B.Bot('192.168.1.5', self.port, '123456', 'QA_001', 2)
        for bad in ('123', 'abcdef', '1234567'):
            with self.assertRaises(ValueError):
                B.Bot('127.0.0.1', self.port, bad, 'QA_001', 2)
        for cycles in (0, 26, 100):
            with self.assertRaises(ValueError):
                B.run_suite('127.0.0.1', self.port, '123456', cycles)
        with self.assertRaises(ValueError):
            B.Bot('127.0.0.1', self.port, '123456', '../save', 2)


if __name__ == '__main__':
    unittest.main()


class RealEHL8ServerTests(unittest.TestCase):
    """Production EHL8 integration whenever this test runs inside the full repo."""
    def test_real_session_server_pair_relay_and_rejoin(self):
        actual = Path(__file__).resolve().parents[1] / 'tools' / 'emerald_session_server.py'
        if not actual.is_file():
            self.skipTest('Bundle-only source: production EHL8 server is in the main repository')
        import asyncio
        import importlib.util
        spec = importlib.util.spec_from_file_location('emerald_session_server', actual)
        srvmod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = srvmod
        spec.loader.exec_module(srvmod)
        loop = asyncio.new_event_loop()
        server = srvmod.SessionServer('123456', slots=2, idle_seconds=900)
        started = threading.Event()
        result = {}
        def serve():
            asyncio.set_event_loop(loop)
            async def begin():
                await server.start('127.0.0.1', 0)
                result['port'] = server.listener.sockets[0].getsockname()[1]
                started.set()
            loop.run_until_complete(begin())
            loop.run_forever()
            loop.run_until_complete(server.stop())
            loop.close()
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        self.assertTrue(started.wait(5))
        try:
            summary = B.run_suite('127.0.0.1', result['port'], '123456', cycles=4, timeout=3)
            self.assertEqual(summary['rounds_passed'], 4, summary['errors'])
            self.assertEqual(summary['identities_attempted'], 8)
        finally:
            loop.call_soon_threadsafe(loop.stop)
            thread.join(timeout=6)
            self.assertFalse(thread.is_alive())
