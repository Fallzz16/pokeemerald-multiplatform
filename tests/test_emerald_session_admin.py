"""EHL8 M2.1-B local administration; validates a real locked JOIN."""
import asyncio
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import emerald_session_server as S

class AdminTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = S.SessionServer("123456", idle_seconds=100)

    async def test_lock_unlock(self):
        self.assertFalse(self.server.locked)
        self.assertTrue(await self.server.admin_command("LOCK ON"))
        self.assertTrue(self.server.locked)
        self.assertFalse(await self.server.admin_command("START"))
        self.assertTrue(await self.server.admin_command("LOCK OFF"))
        self.assertFalse(self.server.locked)

    async def test_kick_only_selected_profile(self):
        class Peer:
            def __init__(self, profile):
                self.profile = profile
                self.closed = False
                self.messages = []
            async def send(self, kind, data, session):
                self.messages.append((kind, data, session))
            def close(self):
                self.closed = True
        a, b = Peer(b"QA_A"), Peer(b"QA_B")
        self.server.players = {1: a, 2: b}
        self.assertFalse(await self.server.admin_command("KICK OTHER"))
        self.assertFalse(await self.server.admin_command("KICK QA_B\nLOCK OFF"))
        self.assertTrue(await self.server.admin_command("KICK QA_B"))
        self.assertTrue(b.closed)
        self.assertFalse(a.closed)
        self.assertEqual(b.messages, [(S.KICK, b"Removed by host", self.server.session)])

    async def test_locked_join_over_real_tcp(self):
        await self.server.start(port=0)
        try:
            await self.server.admin_command("LOCK ON")
            port = self.server.listener.sockets[0].getsockname()[1]
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            try:
                writer.write(S.encode(S.Packet(S.HELLO)))
                await writer.drain()
                welcome = await asyncio.wait_for(S.read_frame(reader), 2)
                self.assertEqual(welcome.kind, S.WELCOME)
                writer.write(S.encode(S.Packet(S.AUTH_PIN, b"123456", welcome.session)))
                await writer.drain()
                reply = await asyncio.wait_for(S.read_frame(reader), 2)
                self.assertEqual(reply.kind, S.AUTH_PIN)
                writer.write(S.encode(S.Packet(S.JOIN, b"QA_A", welcome.session)))
                await writer.drain()
                kick = await asyncio.wait_for(S.read_frame(reader), 2)
                self.assertEqual(kick.kind, S.KICK)
                self.assertEqual(kick.payload, b"Lobby locked")
                self.assertFalse(self.server.players)
            finally:
                writer.close()
                await writer.wait_closed()
        finally:
            await self.server.stop()

if __name__ == "__main__":
    unittest.main()
