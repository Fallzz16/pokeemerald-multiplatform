"""M2.3 real EHL8 TCP tests: host-gated start without fake readiness.

The legacy default remains automatic; the flag affects only the private host
session and requires both actual clients to send READY.
"""
import asyncio
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import emerald_session_server as S


class Peer:
    def __init__(self, reader, writer):
        self.reader, self.writer, self.session = reader, writer, 0

    async def send(self, kind, payload=b""):
        self.writer.write(S.encode(S.Packet(kind, payload, self.session)))
        await self.writer.drain()

    async def next(self, kind):
        packet = await asyncio.wait_for(S.read_frame(self.reader), 3)
        assert packet.kind == kind, (packet.kind, kind)
        return packet

    async def join(self, profile):
        await self.send(S.HELLO)
        self.session = (await self.next(S.WELCOME)).session
        await self.send(S.AUTH_PIN, b"123456")
        await self.next(S.AUTH_PIN)
        await self.send(S.JOIN, profile)
        slot = (await self.next(S.JOIN)).payload[0]
        await self.next(S.PLAYER_LIST)
        return slot

    async def close(self):
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except (OSError, ConnectionError):
            pass


class HostStart(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = S.SessionServer("123456", manual_start=True)
        listener = await self.server.start("127.0.0.1", 0)
        self.port = listener.sockets[0].getsockname()[1]
        self.clients = []

    async def asyncTearDown(self):
        for client in self.clients:
            await client.close()
        await self.server.stop()

    async def connect(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        client = Peer(reader, writer)
        self.clients.append(client)
        return client

    async def test_needs_two_ready_and_explicit_start(self):
        self.assertFalse(await self.server.admin_command("START"))
        a, b = await self.connect(), await self.connect()
        self.assertEqual(await a.join(b"QA_A"), 1)
        self.assertFalse(await self.server.admin_command("START"))
        self.assertEqual(await b.join(b"QA_B"), 2)
        await a.next(S.PLAYER_LIST)
        await a.send(S.READY, b"\x01")
        await a.next(S.PLAYER_LIST)
        await b.next(S.PLAYER_LIST)
        self.assertFalse(await self.server.admin_command("START"))
        await b.send(S.READY, b"\x01")
        await a.next(S.PLAYER_LIST)
        await b.next(S.PLAYER_LIST)
        self.assertEqual(sum(p.ready for p in self.server.players.values()), 2)
        self.assertFalse(self.server.in_game)
        self.assertTrue(all(p.stage == "LOBBY" for p in self.server.players.values()))
        # Clients can remain waiting for the host and still exchange heartbeats.
        await b.send(S.HEARTBEAT)
        await b.next(S.HEARTBEAT)
        self.assertFalse(self.server.in_game)
        self.assertTrue(await self.server.admin_command("START"))
        await a.next(S.START)
        await b.next(S.START)
        self.assertTrue(self.server.in_game)
        self.assertTrue(all(p.stage == "GAME" for p in self.server.players.values()))
        self.assertFalse(await self.server.admin_command("START"))
        await b.close()
        await a.next(S.LEAVE)
        await a.next(S.PLAYER_LIST)
        self.assertTrue(self.server.in_game, "survivor must continue playing")

    async def test_unready_blocks_start_and_ready_can_be_revoked(self):
        a, b = await self.connect(), await self.connect()
        await a.join(b"QA_A")
        await b.join(b"QA_B")
        await a.next(S.PLAYER_LIST)
        for current, other in [(a, b), (b, a)]:
            await current.send(S.READY, b"\x01")
            await current.next(S.PLAYER_LIST)
            await other.next(S.PLAYER_LIST)
        await a.send(S.READY, b"\x00")
        await a.next(S.PLAYER_LIST)
        await b.next(S.PLAYER_LIST)
        self.assertFalse(await self.server.admin_command("START"))
        self.assertFalse(self.server.in_game)
        await a.send(S.READY, b"\x01")
        await a.next(S.PLAYER_LIST)
        await b.next(S.PLAYER_LIST)
        self.assertTrue(await self.server.admin_command("START"))
        await a.next(S.START)
        await b.next(S.START)

    async def test_legacy_auto_start_unchanged(self):
        legacy = S.SessionServer("123456")
        self.assertFalse(legacy.manual_start)
        self.assertFalse(await legacy.admin_command("START"))
        self.assertFalse(legacy.in_game)


if __name__ == "__main__":
    unittest.main()
