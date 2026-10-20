"""Real loopback TCP tests against the EHL8 dedicated session server."""
import asyncio
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

    async def test_running_room_ready_ack_does_not_disconnect(self):
        a, b = await self.connect(), await self.connect()
        await a.begin("one")
        await b.begin("two")
        await a.recv(S.PLAYER_LIST)
        for player, other in ((a, b), (b, a)):
            await player.send(S.READY, bytes([1]))
            await player.recv(S.PLAYER_LIST)
            await other.recv(S.PLAYER_LIST)
        await a.recv(S.START)
        await b.recv(S.START)
        await b.close()
        await a.recv(S.LEAVE)
        await a.recv(S.PLAYER_LIST)
        late = await self.connect()
        await late.begin("three")
        await a.recv(S.PLAYER_LIST)
        await late.recv(S.START)
        await late.send(S.READY, bytes([1]))
        await a.recv(S.PLAYER_LIST)
        await late.recv(S.PLAYER_LIST)
        # Repeated READY is harmless and must not flood PLAYER_LIST.
        await late.send(S.READY, bytes([1]))
        await late.send(S.HEARTBEAT)
        await late.recv(S.HEARTBEAT)
        self.assertEqual(len(self.server.players), 2)
        pose = bytearray(18)
        pose[:5] = bytes([76, 65, 78, 80, 1])
        pose[5], pose[14] = 1, 2
        pose[6:8] = (1).to_bytes(2, "big")
        await late.send(S.POSE, bytes(pose))
        self.assertEqual((await a.recv(S.POSE)).payload, bytes([2]) + bytes(pose))

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
        attempts, blocked_until, last_failed = self.server.invalid_attempts["127.0.0.1"]
        self.assertEqual(attempts, 3)
        self.assertGreater(last_failed, 0)
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

    async def test_pending_auth_cannot_bypass_an_active_cooldown(self):
        # Open a legitimate-looking socket before the wrong-PIN failures.
        pending = await self.connect()
        await pending.send(S.HELLO)
        pending.session = (await pending.recv(S.WELCOME)).session
        for _ in range(3):
            offender = await self.connect()
            await offender.begin("unused", pin=b"000000")
        # A correct PIN on that already-open socket must still be refused.
        await pending.send(S.AUTH_PIN, b"123456")
        response = await pending.recv(S.KICK)
        self.assertIn(b"cooldown", response.payload)
        self.assertEqual(self.server.invalid_attempts["127.0.0.1"][0], 3)
        self.assertFalse(self.server.players)

    async def test_valid_pin_clears_previous_typo_count(self):
        # A correct PIN must reset ordinary mistakes for this address.
        for _ in range(2):
            peer = await self.connect()
            await peer.begin("unused", pin=b"000000")
        self.assertEqual(self.server.invalid_attempts["127.0.0.1"][0], 2)
        good = await self.connect()
        await good.begin("safe")
        self.assertNotIn("127.0.0.1", self.server.invalid_attempts)
        again = await self.connect()
        await again.begin("unused", pin=b"000000")
        self.assertEqual(self.server.invalid_attempts["127.0.0.1"][0], 1)

    def test_pin_failure_window_expires_and_resets(self):
        address = "192.168.0.11"
        s = self.server
        s._record_invalid_pin(address, 100.0)
        s._record_invalid_pin(address, 101.0)
        self.assertEqual(s.invalid_attempts[address][0], 2)
        s._prune_pin_failures(101.0 + S.PIN_FAILURE_WINDOW_SECONDS + 1)
        self.assertNotIn(address, s.invalid_attempts)
        s._record_invalid_pin(address, 2000.0)
        self.assertEqual(s.invalid_attempts[address][0], 1)

    def test_pin_failure_tracking_is_bounded_and_respects_cooldowns(self):
        s = self.server
        now = 5000.0
        for n in range(S.PIN_MAX_TRACKED_ADDRESSES + 40):
            address = f"192.0.{n // 256}.{n % 256}"
            self.assertTrue(s._allow_pin_address(address, now))
            s._record_invalid_pin(address, now)
            self.assertLessEqual(len(s.invalid_attempts), S.PIN_MAX_TRACKED_ADDRESSES)
        self.assertEqual(len(s.invalid_attempts), S.PIN_MAX_TRACKED_ADDRESSES)
        # Active blocks must not be evicted solely to admit a new source.
        s.invalid_attempts = {
            f"blocked-{n}": (3, now + 100, now)
            for n in range(S.PIN_MAX_TRACKED_ADDRESSES)
        }
        self.assertFalse(s._allow_pin_address("new", now))
        self.assertEqual(len(s.invalid_attempts), S.PIN_MAX_TRACKED_ADDRESSES)
        self.assertTrue(s._allow_pin_address("new", now + 101))

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

    async def test_single_lobby_status_line_includes_reservations_without_secrets(self):
        player = await self.connect()
        await player.begin("HOST_A")
        with self.assertLogs("emerald.session", level="INFO") as captured:
            self.server.log_room_state()
        self.assertIn("EHL8_ROOM_STATE=1/2,0/2,0,0/2",
                      captured.output[-1])
        self.assertNotIn("123456", captured.output[-1])
        self.server.reservations[2] = S.Reservation(
            b"GUEST_B", b"x" * S.RESUME_TOKEN_BYTES,
            S.time.monotonic() + 60)
        with self.assertLogs("emerald.session", level="INFO") as captured:
            self.server.log_room_state()
        self.assertIn("EHL8_ROOM_STATE=1/2,0/2,0,1/2",
                      captured.output[-1])

    def test_expiring_last_reservation_unsets_started_session(self):
        self.server.in_game = True
        self.server.reservations[1] = S.Reservation(
            b"QA_A", b"x" * S.RESUME_TOKEN_BYTES,
            S.time.monotonic() - 1)
        with self.assertLogs("emerald.session", level="INFO") as captured:
            self.server.expire_reservations()
        self.assertFalse(self.server.in_game)
        self.assertFalse(self.server.reservations)
        self.assertTrue(any("EHL8_ROOM_STARTED=0" in line
                            for line in captured.output))
        self.assertTrue(any("EHL8_ROOM_STATE=0/2,0/2,0,0/2" in line
                            for line in captured.output))

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
