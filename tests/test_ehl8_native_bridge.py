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
        # Separate short-timeout binary for an accelerated but REAL C-client
        # waiting-room test. Existing native test timeouts stay unchanged.
        cls.wait_exe = str(Path(cls.tmp.name) / "native_ehl8_wait_start")
        cmd_wait = cmd[:cmd.index("tests/native_ehl8_client.c")] + [
            "-DEHL_AUTH_TIMEOUT_MS=2300UL",
            "tests/native_ehl8_client.c", "-o", cls.wait_exe]
        subprocess.run(cmd_wait, cwd=ROOT, check=True, timeout=45)

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

    async def test_two_native_clients_remain_ready_without_start_then_play(self):
        # Unlike Python fake clients, these processes use the actual C
        # socket / state machine / automatic heartbeat implementation.
        # An accelerated 2.3 s WAIT_START timeout would kick a native client
        # that failed to emit heartbeat before the host's delayed START.
        class HostServer(server_module.SessionServer):
            def __init__(self):
                super().__init__("123456", 2, idle_seconds=300, manual_start=True)
                self.wait_heartbeats = {}

            async def process(self, peer, msg):
                if msg.kind == server_module.HEARTBEAT and peer.stage == "LOBBY":
                    name = peer.profile
                    self.wait_heartbeats[name] = self.wait_heartbeats.get(name, 0) + 1
                await super().process(peer, msg)

        server = HostServer()
        listener = await server.start("127.0.0.1", 0)
        port = str(listener.sockets[0].getsockname()[1])
        clients = [
            await asyncio.create_subprocess_exec(
                self.wait_exe, "127.0.0.1", port,
                "123456", "wait_A" if index == 0 else "wait_B",
                "21" if index == 0 else "34",
                "34" if index == 0 else "21", "awaitstart",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            for index in range(2)
        ]
        try:
            for _ in range(100):
                if len(server.players) == 2 and all(p.ready for p in server.players.values()):
                    break
                await asyncio.sleep(0.03)
            self.assertEqual(len(server.players), 2, "native C clients never became READY")
            self.assertFalse(server.in_game, "manual host started without permission")
            await asyncio.sleep(3.25)
            self.assertFalse(server.in_game)
            self.assertEqual(len(server.players), 2, "native clients timed out while waiting")
            for who in (b"wait_A", b"wait_B"):
                self.assertGreaterEqual(server.wait_heartbeats.get(who, 0), 3, who)
            self.assertTrue(await server.admin_command("START"))
            output = await asyncio.wait_for(
                asyncio.gather(*(c.communicate() for c in clients)), timeout=10)
            for process, (stdout, stderr) in zip(clients, output):
                self.assertEqual(process.returncode, 0, stderr)
                self.assertIn(b"native WAIT_START heartbeats", stdout)
        finally:
            for process in clients:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
            await server.stop()

    async def test_real_native_game_clients_decode_two_ready_players(self):
        """Validates C PLAYER_LIST decoding against the REAL Python EHL8 server."""
        server = server_module.SessionServer("123456", 2, idle_seconds=300)
        listener = await server.start("127.0.0.1", 0)
        port = str(listener.sockets[0].getsockname()[1])
        clients = [
            await asyncio.create_subprocess_exec(
                self.exe, "127.0.0.1", port, "123456",
                "trainer_A" if i == 0 else "trainer_B",
                "21" if i == 0 else "34",
                "34" if i == 0 else "21", "roster",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            for i in range(2)
        ]
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*(p.communicate() for p in clients)), timeout=16)
            for child, (out, err) in zip(clients, results):
                self.assertEqual(child.returncode, 0, err)
                self.assertIn(b"native PLAYER_LIST 2/2 READY", out)
            self.assertTrue(server.in_game)
        finally:
            for child in clients:
                if child.returncode is None:
                    child.kill()
                    await child.wait()
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
