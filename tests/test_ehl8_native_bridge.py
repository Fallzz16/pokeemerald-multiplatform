"""Tests real native C SessionClient ↔ Python EHL8 dedicated server on TCP loopback.
Compiles checked-in C sources into ephemeral binary. No .sav, no game boot.
"""
import asyncio
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("emerald_session_server", ROOT / "tools/emerald_session_server.py")
server_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = server_module
spec.loader.exec_module(server_module)

class NativeBridge(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = str(Path(cls.tmp.name) / "native_ehl8_client")
        cmd = ["gcc", "-std=c99", "-DPORTABLE", "-D_POSIX_C_SOURCE=200809L",
               "-Wall", "-Wextra", "-Werror", "-O1", "-g", "-Isrc/lnet",
               "src/lnet/lnet_net.c", "src/lnet/lnet_session_v1.c",
               "src/lnet/lnet_presence.c", "src/lnet/lnet_session_client.c",
               "tests/native_ehl8_client.c", "-o", cls.exe]
        subprocess.run(cmd, cwd=ROOT, check=True, timeout=45)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    async def test_two_native_client_processes_render_remote_overworld(self):
        server = server_module.SessionServer("123456", 2, idle_seconds=300)
        listener = await server.start("127.0.0.1", 0)
        port = str(listener.sockets[0].getsockname()[1])
        a = await asyncio.create_subprocess_exec(self.exe, "127.0.0.1", port,
            "123456", "trainer_A", "21", "34", stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        b = await asyncio.create_subprocess_exec(self.exe, "127.0.0.1", port,
            "123456", "trainer_B", "34", "21", stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        try:
            results = await asyncio.wait_for(asyncio.gather(a.communicate(), b.communicate()), 16)
            self.assertEqual(a.returncode, 0, results[0])
            self.assertEqual(b.returncode, 0, results[1])
            self.assertIn(b"remote overworld pose verified", results[0][0])
            self.assertIn(b"remote overworld pose verified", results[1][0])
        finally:
            for p in (a,b):
                if p.returncode is None:
                    p.kill()
                    await p.wait()
            await server.stop()

    async def test_wrong_pin_native_client_fails_without_changing_existing_lobby(self):
        server = server_module.SessionServer("123456", 2, idle_seconds=300)
        listener = await server.start("127.0.0.1", 0)
        port = str(listener.sockets[0].getsockname()[1])
        bad = await asyncio.create_subprocess_exec(self.exe, "127.0.0.1", port,
            "555555", "wrong_pin", "21", "34", stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        try:
            await asyncio.wait_for(bad.communicate(), 8)
            self.assertNotEqual(bad.returncode, 0)
            self.assertFalse(server.players, "Failed PIN must never create a lobby member")
            self.assertFalse(server.in_game)
        finally:
            if bad.returncode is None:
                bad.kill()
                await bad.wait()
            await server.stop()

    async def test_native_rejected_duplicate_profile_cannot_replace_existing(self):
        server = server_module.SessionServer("123456", 2, idle_seconds=300)
        listener = await server.start("127.0.0.1", 0)
        port = str(listener.sockets[0].getsockname()[1])
        a = await asyncio.create_subprocess_exec(self.exe, "127.0.0.1", port,
            "123456", "trainer_A", "21", "34", stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        try:
            for _ in range(80):
                await asyncio.sleep(.025)
                if server.players:
                    break
            self.assertEqual(len(server.players), 1)
            duplicate = await asyncio.create_subprocess_exec(self.exe, "127.0.0.1", port,
                "123456", "trainer_A", "34", "21", stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            try:
                await asyncio.wait_for(duplicate.communicate(), 8)
                self.assertNotEqual(duplicate.returncode, 0)
                self.assertEqual(len(server.players), 1)
                self.assertEqual(next(iter(server.players.values())).profile, b"trainer_A")
            finally:
                if duplicate.returncode is None:
                    duplicate.kill()
                    await duplicate.wait()
        finally:
            if a.returncode is None:
                a.kill()
                await a.wait()
            await server.stop()


    async def test_native_auto_rejoins_same_reserved_slot_after_tcp_failure(self):
        """Drop the real C client's socket mid-game and verify recovery."""
        server = server_module.SessionServer("123456", 2, idle_seconds=300)
        listener = await server.start("127.0.0.1", 0)
        port = str(listener.sockets[0].getsockname()[1])
        native = await asyncio.create_subprocess_exec(
            self.exe, "127.0.0.1", port, "123456", "trainer_A",
            "21", "34", "--expect-reconnect", stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        writer = None
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", int(port))
            async def send(kind, data=b"", sid=0):
                writer.write(server_module.encode(server_module.Packet(kind, data, sid)))
                await writer.drain()
            await send(server_module.HELLO)
            welcome = await server_module.read_frame(reader)
            self.assertEqual(welcome.kind, server_module.WELCOME)
            sid = welcome.session
            await send(server_module.AUTH_PIN, b"123456", sid)
            self.assertEqual((await server_module.read_frame(reader)).kind,
                             server_module.AUTH_PIN)
            await send(server_module.JOIN, b"python_peer", sid)
            self.assertEqual((await server_module.read_frame(reader)).kind,
                             server_module.JOIN)
            await send(server_module.READY, b"\\x01", sid)
            for _ in range(100):
                if server.in_game and len(server.players) == 2:
                    break
                await asyncio.sleep(.04)
            self.assertTrue(server.in_game)
            self.assertEqual(len(server.players), 2)
            await asyncio.sleep(.25)
            original_slot = next(slot for slot,p in server.players.items()
                                 if p.profile == b"trainer_A")
            server.players[original_slot].close()
            for _ in range(80):
                if b"trainer_A" in server.reservations:
                    break
                await asyncio.sleep(.02)
            self.assertEqual(server.reservations[b"trainer_A"][0], original_slot)
            result_task = asyncio.create_task(native.communicate())
            for seq in range(1, 130):
                if result_task.done():
                    break
                pose=bytearray(18)
                pose[:5]=b"LANP\\x01"
                pose[5], pose[14] = 1, 2
                pose[6:8] = seq.to_bytes(2, "big")
                pose[10:12] = (34).to_bytes(2, "big")
                await send(server_module.POSE, bytes(pose), sid)
                await asyncio.sleep(.13)
            out, err = await asyncio.wait_for(result_task, 5)
            self.assertEqual(native.returncode, 0, (out,err))
            self.assertIn(b"native reconnect and remote pose verified", out)
            self.assertNotIn(b"trainer_A", server.reservations)
            self.assertEqual(server.players[original_slot].profile, b"trainer_A")
        finally:
            if native.returncode is None:
                native.kill()
                await native.wait()
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except (ConnectionError, OSError):
                    pass
            await server.stop()

if __name__ == "__main__":
    unittest.main(verbosity=2)
