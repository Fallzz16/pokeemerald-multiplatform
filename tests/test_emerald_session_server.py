"""Real loopback TCP tests against the EHL8 dedicated session server."""
import asyncio
import json
from pathlib import Path
import tempfile
import importlib.util
from pathlib import Path
import struct
import sys
import unittest

module_path = Path(__file__).resolve().parents[1] / "tools" / "emerald_session_server.py"
spec = importlib.util.spec_from_file_location("emerald_session_server", module_path)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)

class Client:
    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.session = 0
    async def send(self, kind, payload=b"", session=None):
        self.writer.write(S.encode(S.Packet(kind, payload, self.session if session is None else session)))
        await self.writer.drain()
    async def recv(self, kind):
        packet = await asyncio.wait_for(S.read_frame(self.reader), 3)
        assert packet.kind == kind, (packet.kind, kind, packet.payload)
        return packet
    async def begin(self, profile, pin=b"123456"):
        await self.send(S.HELLO)
        welcome = await self.recv(S.WELCOME)
        self.session = welcome.session
        await self.send(S.AUTH_PIN, pin)
        if pin != b"123456":
            return await self.recv(S.KICK)
        await self.recv(S.AUTH_PIN)
        await self.send(S.JOIN, profile.encode("ascii"))
        join = await self.recv(S.JOIN)
        await self.recv(S.PLAYER_LIST)
        return join
    async def close(self):
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except (ConnectionError, OSError):
            pass

class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = S.SessionServer("123456", idle_seconds=900)
        listener = await self.server.start("127.0.0.1", 0)
        self.port = listener.sockets[0].getsockname()[1]
        self.clients = []
    async def asyncTearDown(self):
        for c in self.clients:
            await c.close()
        await self.server.stop()
        await asyncio.sleep(.03)
    async def connect(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        client = Client(reader, writer)
        self.clients.append(client)
        return client

    async def test_local_status_reports_actual_players_ready_and_shutdown(self):
        with tempfile.TemporaryDirectory() as temp:
            status_file = Path(temp) / "room.json"
            self.server.status_file = status_file
            self.server.write_status()
            start = json.loads(status_file.read_text(encoding="utf-8"))
            self.assertEqual(start["state"], "lobby")
            self.assertEqual(start["capacity"], 2)
            self.assertEqual(start["port"], self.port)
            self.assertEqual(start["players"], [])

            a = await self.connect()
            await a.begin("alpha")
            snapshot = json.loads(status_file.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["players"], [
                {"slot": 1, "profile": "alpha", "ready": False}])

            b = await self.connect()
            await b.send(S.HELLO)
            b.session = (await b.recv(S.WELCOME)).session
            await b.send(S.AUTH_PIN, b"123456")
            await b.recv(S.AUTH_PIN)
            await b.send(S.JOIN, b"beta")
            await b.recv(S.JOIN)
            await b.recv(S.PLAYER_LIST)
            await a.recv(S.PLAYER_LIST)
            await a.send(S.READY, b"\x01")
            await a.recv(S.PLAYER_LIST)
            await b.recv(S.PLAYER_LIST)
            data = json.loads(status_file.read_text(encoding="utf-8"))
            self.assertEqual([p["ready"] for p in data["players"]], [True, False])

            await b.send(S.READY, b"\x01")
            await a.recv(S.PLAYER_LIST)
            await b.recv(S.PLAYER_LIST)
            await a.recv(S.START)
            await b.recv(S.START)
            active = json.loads(status_file.read_text(encoding="utf-8"))
            self.assertEqual(active["state"], "playing")
            self.assertEqual(len(active["players"]), 2)
            self.assertNotIn("123456", status_file.read_text(encoding="utf-8"))
            self.assertNotIn("pin", active)

            await b.close()
            await a.recv(S.LEAVE)
            await a.recv(S.PLAYER_LIST)
            after = json.loads(status_file.read_text(encoding="utf-8"))
            self.assertEqual([p["profile"] for p in after["players"]], ["alpha"])
            await self.server.stop()
            stopped = json.loads(status_file.read_text(encoding="utf-8"))
            self.assertEqual(stopped["state"], "stopped")

    async def test_two_clients_lobby_ready_start_and_poses(self):
        a, b = await self.connect(), await self.connect()
        self.assertEqual((await a.begin("one")).payload, b"\x01")
        await b.send(S.HELLO)
        b.session = (await b.recv(S.WELCOME)).session
        await b.send(S.AUTH_PIN, b"123456")
        await b.recv(S.AUTH_PIN)
        await b.send(S.JOIN, b"two")
        self.assertEqual((await b.recv(S.JOIN)).payload, b"\x02")
        await b.recv(S.PLAYER_LIST)
        await a.recv(S.PLAYER_LIST)
        await a.send(S.READY, b"\x01")
        await a.recv(S.PLAYER_LIST)
        await b.recv(S.PLAYER_LIST)
        await b.send(S.READY, b"\x01")
        await a.recv(S.PLAYER_LIST)
        await b.recv(S.PLAYER_LIST)
        await a.recv(S.START)
        await b.recv(S.START)
        self.assertTrue(self.server.in_game)
        pose = bytearray(18)
        pose[:5] = b"LANP\x01"
        pose[5] = 1
        pose[6:8] = b"\x00\x01"
        pose[10:12] = (20).to_bytes(2, "big")
        pose[12:14] = (24).to_bytes(2, "big")
        pose[14] = 2
        await a.send(S.POSE, bytes(pose))
        self.assertEqual((await b.recv(S.POSE)).payload, b"\x01" + bytes(pose))
        await b.send(S.HEARTBEAT)
        await b.recv(S.HEARTBEAT)

    async def test_reject_duplicate_and_third_player(self):
        a, b, c = await self.connect(), await self.connect(), await self.connect()
        await a.begin("same")
        await b.send(S.HELLO)
        b.session = (await b.recv(S.WELCOME)).session
        await b.send(S.AUTH_PIN, b"123456")
        await b.recv(S.AUTH_PIN)
        await b.send(S.JOIN, b"same")
        self.assertIn(b"Profile already active", (await b.recv(S.KICK)).payload)
        await c.begin("different")
        self.assertEqual(len(self.server.players), 2)
        d = await self.connect()
        await d.send(S.HELLO)
        d.session = (await d.recv(S.WELCOME)).session
        await d.send(S.AUTH_PIN, b"123456")
        await d.recv(S.AUTH_PIN)
        await d.send(S.JOIN, b"third")
        self.assertIn(b"full", (await d.recv(S.KICK)).payload)

    async def test_bad_header_and_excess_payload_never_crash_listener(self):
        for bad in (
            b"BAD!" + b"\x00" * 24,
            S.HEADER.pack(b"EHL8", 1, 0, 1, 0, 500000, 0, 0),
            S.HEADER.pack(b"EHL8", 2, 0, 1, 0, 0, 0, 0),
        ):
            a = await self.connect()
            a.writer.write(bad)
            await a.writer.drain()
            self.assertEqual(await asyncio.wait_for(a.reader.read(), 2), b"")
        good = await self.connect()
        await good.begin("safe")
        self.assertEqual(len(self.server.players), 1)
        with self.assertRaises(S.ProtocolError):
            S.encode(S.Packet(S.HELLO, b"x" * 4097))

    async def test_three_invalid_pins_trigger_per_ip_cooldown(self):
        for _ in range(3):
            peer = await self.connect()
            await peer.begin("unused", pin=b"000000")
        attempts, blocked_until = self.server.invalid_attempts["127.0.0.1"]
        self.assertEqual(attempts, 3)
        self.assertGreater(blocked_until, S.time.monotonic())
        peer = await self.connect()
        await peer.send(S.HELLO)
        try:
            # On Linux, closing a socket with unread handshake bytes may
            # produce ECONNRESET; Windows may report EOF. Both indicate
            # correctly refused new clients after the PIN cooldown.
            self.assertEqual(await asyncio.wait_for(peer.reader.read(), 2), b"")
        except ConnectionResetError:
            pass

    async def test_invalid_pose_disconnected_and_peer_survives(self):
        a, b = await self.connect(), await self.connect()
        await a.begin("one")
        await b.send(S.HELLO)
        b.session = (await b.recv(S.WELCOME)).session
        await b.send(S.AUTH_PIN, b"123456")
        await b.recv(S.AUTH_PIN)
        await b.send(S.JOIN, b"two")
        await b.recv(S.JOIN)
        await b.recv(S.PLAYER_LIST)
        await a.recv(S.PLAYER_LIST)
        for p, q in ((a, b), (b, a)):
            await p.send(S.READY, b"\x01")
            await p.recv(S.PLAYER_LIST)
            await q.recv(S.PLAYER_LIST)
        await a.recv(S.START)
        await b.recv(S.START)
        await a.send(S.POSE, b"malformed")
        await b.recv(S.LEAVE)
        await b.recv(S.PLAYER_LIST)
        self.assertEqual(len(self.server.players), 1)

    def test_validation(self):
        x = bytearray(18)
        x[:5] = b"LANP\x01"
        x[5], x[14] = 1, 2
        self.assertTrue(S.valid_pose(bytes(x)))
        x[10:12] = struct.pack(">H", 2048)
        self.assertFalse(S.valid_pose(bytes(x)))
        with self.assertRaises(ValueError):
            S.SessionServer("wrong-pin")
        with self.assertRaises(ValueError):
            S.SessionServer("123456", slots=4)

if __name__ == "__main__":
    unittest.main(verbosity=2)
