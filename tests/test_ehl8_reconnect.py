"""Real loopback regression tests for 60-second EHL8 reconnect."""
import asyncio
import importlib.util
import pathlib
import sys
import unittest
p = pathlib.Path(__file__).resolve().parents[1] / "tools" / "emerald_session_server.py"
spec = importlib.util.spec_from_file_location("resumable_session", p)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)

class ReconnectTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.srv = S.SessionServer("123456")
        listener = await self.srv.start("127.0.0.1", 0)
        self.port = listener.sockets[0].getsockname()[1]
        self.streams = []

    async def asyncTearDown(self):
        for reader, writer in self.streams:
            writer.close()
            try: await writer.wait_closed()
            except OSError: pass
        await self.srv.stop()

    async def connect(self, identity, resume=None):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        self.streams.append((reader, writer))
        async def step(typ, value=b"", session=0):
            writer.write(S.encode(S.Packet(typ, value, session)))
            await writer.drain()
        await step(S.HELLO)
        hello = await S.read_frame(reader)
        self.assertEqual(hello.kind, S.WELCOME)
        await step(S.AUTH_PIN, b"123456", hello.session)
        self.assertEqual((await S.read_frame(reader)).kind, S.AUTH_PIN)
        payload = identity + b"\x00" + (resume or b"")
        await step(S.JOIN, payload, hello.session)
        result = await S.read_frame(reader)
        return reader, writer, hello.session, result

    async def test_slot_reservation_resume_and_rotation(self):
        ra, wa, sa, first = await self.connect(b"alice")
        self.assertEqual(first.payload[0], 1)
        self.assertEqual(len(first.payload), 17)
        token = first.payload[1:]
        self.assertEqual((await S.read_frame(ra)).kind, S.PLAYER_LIST)
        wa.close()
        for _ in range(100):
            if self.srv.reservations: break
            await asyncio.sleep(.005)
        self.assertIn(1, self.srv.reservations)
        rb, wb, sb, blocked = await self.connect(b"alice")
        self.assertEqual(blocked.kind, S.KICK)
        self.assertIn(b"reserved", blocked.payload)
        rc, wc, sc, resumed = await self.connect(b"alice", token)
        self.assertEqual(resumed.kind, S.JOIN)
        self.assertEqual(resumed.payload[0], 1)
        self.assertNotEqual(resumed.payload[1:], token)
        self.assertNotIn(1, self.srv.reservations)

    async def test_expiry_and_new_identity(self):
        reader, writer, sid, join = await self.connect(b"alice")
        self.assertEqual((await S.read_frame(reader)).kind, S.PLAYER_LIST)
        writer.close()
        for _ in range(100):
            if self.srv.reservations: break
            await asyncio.sleep(.005)
        hold = self.srv.reservations[1]
        self.srv.reservations[1] = S.Reservation(1, hold.profile, hold.secret,
                                                 S.time.monotonic() - 1)
        self.srv.prune_reservations()
        self.assertEqual(self.srv.reservations, {})
        rx, wx, sx, fresh = await self.connect(b"newcomer")
        self.assertEqual(fresh.kind, S.JOIN)
        self.assertEqual(fresh.payload[0], 1)

    async def test_voluntary_leave_clears_reservation(self):
        reader, writer, sid, first = await self.connect(b"alice")
        await S.read_frame(reader)
        writer.write(S.encode(S.Packet(S.LEAVE, b"", sid)))
        await writer.drain()
        for _ in range(100):
            if not self.srv.players: break
            await asyncio.sleep(.005)
        self.assertFalse(self.srv.reservations)

if __name__ == "__main__":
    unittest.main()
