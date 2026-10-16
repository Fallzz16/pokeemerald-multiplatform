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
               "-Wall", "-Wextra", "-Werror", "-O1", "-g",
               "-DEHL_HEARTBEAT_INTERVAL_MS=250UL", "-Isrc/lnet",
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

    async def test_playing_clients_send_heartbeats_even_while_streaming_poses(self):
        # The game sends poses every 100 ms. Heartbeats must still be sent;
        # the test overrides only the heartbeat interval to 250 ms so it runs
        # in under two seconds rather than sleeping for ten production seconds.
        class CountingServer(server_module.SessionServer):
            def __init__(self):
                super().__init__("123456", 2, idle_seconds=300)
                self.playing_heartbeats = {}

            async def process(self, peer, msg):
                if msg.kind == server_module.HEARTBEAT and peer.stage == "GAME":
                    who = peer.profile
                    self.playing_heartbeats[who] = self.playing_heartbeats.get(who, 0) + 1
                await super().process(peer, msg)

        server = CountingServer()
        listener = await server.start("127.0.0.1", 0)
        port = str(listener.sockets[0].getsockname()[1])
        a = await asyncio.create_subprocess_exec(self.exe, "127.0.0.1", port,
            "123456", "trainer_A", "21", "34", "linger",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        b = await asyncio.create_subprocess_exec(self.exe, "127.0.0.1", port,
            "123456", "trainer_B", "34", "21", "linger",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            outputs = await asyncio.wait_for(asyncio.gather(a.communicate(), b.communicate()), 8)
            self.assertEqual(a.returncode, 0, outputs[0])
            self.assertEqual(b.returncode, 0, outputs[1])
            self.assertGreaterEqual(server.playing_heartbeats.get(b"trainer_A", 0), 2)
            self.assertGreaterEqual(server.playing_heartbeats.get(b"trainer_B", 0), 2)
        finally:
            for p in (a, b):
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

if __name__ == "__main__":
    unittest.main(verbosity=2)
