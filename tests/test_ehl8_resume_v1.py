import asyncio
"""M2.2 regression tests for the optional EHL8 resume protocol."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import emerald_session_server as S


class Reservations(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_mode_defaults_off(self):
        server = S.SessionServer("123456")
        self.assertFalse(server.resume_enabled)
        self.assertEqual(server.reservations, {})

    async def test_token_format_and_expiry(self):
        server = S.SessionServer("123456", resume_enabled=True)
        class Peer:
            def __init__(self):
                self.resume_token = None
                self.messages = []
            async def send(self, kind, payload, session):
                self.messages.append((kind, payload, session))
        peer = Peer()
        await server.issue_resume_token(peer)
        self.assertEqual(len(peer.resume_token), 32)
        self.assertEqual(peer.messages[0][0], S.RESUME)
        self.assertEqual(peer.messages[0][1], peer.resume_token)


class RealNetworkResume(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = S.SessionServer("123456", resume_enabled=True)
        listener = await self.server.start(port=0)
        self.port = listener.sockets[0].getsockname()[1]
        self.connections = []

    async def asyncTearDown(self):
        for reader, writer, session in self.connections:
            writer.close()
            try:
                await writer.wait_closed()
            except (OSError, ConnectionResetError):
                pass
        await self.server.stop()

    async def send(self, conn, kind, payload=b""):
        reader, writer, session = conn
        writer.write(S.encode(S.Packet(kind, payload, session)))
        await writer.drain()

    async def until(self, conn, kind):
        for _ in range(12):
            p = await asyncio.wait_for(S.read_frame(conn[0]), 2)
            if p.kind == kind:
                return p
            if p.kind == S.KICK:
                return p
        self.fail("Expected EHL8 type was never received")

    async def connect(self, profile, token=None):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        conn = [reader, writer, 0]
        self.connections.append(conn)
        await self.send(conn, S.HELLO)
        welcome = await self.until(conn, S.WELCOME)
        self.assertEqual(welcome.kind, S.WELCOME)
        conn[2] = welcome.session
        await self.send(conn, S.AUTH_PIN, b"123456")
        self.assertEqual((await self.until(conn, S.AUTH_PIN)).payload, b"\x01")
        if token is None:
            await self.send(conn, S.JOIN, profile)
        else:
            await self.send(conn, S.RESUME, profile + b"\x00" + token)
        return conn

    async def join(self, name):
        conn = await self.connect(name)
        joined = await self.until(conn, S.JOIN)
        self.assertEqual(joined.kind, S.JOIN)
        token = (await self.until(conn, S.RESUME)).payload
        self.assertEqual(len(token), 32)
        await self.send(conn, S.READY, b"\x01")
        return conn, joined.payload[0], token

    async def wait_held(self, count):
        for _ in range(100):
            if len(self.server.reservations) == count:
                return
            await asyncio.sleep(.02)
        self.fail("Reservation count mismatch")

    async def test_disconnect_authenticates_rejoin_and_rotates(self):
        a, slot, token = await self.join(b"QA_A")
        b, other, _ = await self.join(b"QA_B")
        self.assertNotEqual(slot, other)
        await self.until(a, S.START)
        await self.until(b, S.START)
        a[1].close()
        await self.wait_held(1)
        self.assertEqual(len(self.server.players), 1)
        self.assertEqual(next(iter(self.server.reservations)), slot)
        denied = await self.connect(b"QA_A")
        self.assertEqual((await self.until(denied, S.KICK)).kind, S.KICK)
        denied = await self.connect(b"QA_A", bytes(32))
        self.assertEqual((await self.until(denied, S.KICK)).kind, S.KICK)
        await self.wait_held(1)
        await self.server.admin_command("LOCK ON")
        reconnected = await self.connect(b"QA_A", token)
        self.assertEqual((await self.until(reconnected, S.JOIN)).payload, bytes([slot]))
        rotated = (await self.until(reconnected, S.RESUME)).payload
        self.assertEqual(len(rotated), 32)
        self.assertNotEqual(rotated, token)
        await self.wait_held(0)
        await self.send(b, S.HEARTBEAT)
        self.assertEqual((await self.until(b, S.HEARTBEAT)).kind, S.HEARTBEAT)
        reconnected[1].close()
        await self.wait_held(1)
        replay = await self.connect(b"QA_A", token)
        self.assertEqual((await self.until(replay, S.KICK)).kind, S.KICK)
        good = await self.connect(b"QA_A", rotated)
        self.assertEqual((await self.until(good, S.JOIN)).payload, bytes([slot]))
        await self.wait_held(0)

    async def test_expiry_and_admin_revoke(self):
        a, slot, token = await self.join(b"QA_A")
        b, _, _ = await self.join(b"QA_B")
        await self.until(a, S.START)
        await self.until(b, S.START)
        a[1].close()
        await self.wait_held(1)
        self.assertTrue(await self.server.admin_command("KICK QA_A"))
        await self.wait_held(0)
        rejected = await self.connect(b"QA_A", token)
        self.assertEqual((await self.until(rejected, S.KICK)).kind, S.KICK)
        third, freed, token3 = await self.join(b"THIRD")
        self.assertEqual(freed, slot)
        third[1].close()
        await self.wait_held(1)
        import time
        current = self.server.reservations[slot]
        self.server.reservations[slot] = S.Reservation(
            current.profile, current.token, time.monotonic() - 1)
        self.server.expire_reservations()
        await self.wait_held(0)
        expired = await self.connect(b"THIRD", token3)
        self.assertEqual((await self.until(expired, S.KICK)).kind, S.KICK)
        newcomer, freed, _ = await self.join(b"NEWCOMER")
        self.assertEqual(freed, slot)
