"""Tests real native C SessionClient ↔ Python EHL8 dedicated server on TCP loopback.
Compiles checked-in C sources into ephemeral binary. No .sav, no game boot.
"""
import asyncio
import importlib.util
import socket
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
        # Short deadline to prove a permanently unavailable listener fails
        # within the configured bound rather than hanging the game forever.
        cls.short_connect_exe = str(Path(cls.tmp.name) / "native_ehl8_short_connect")
        cmd_short = cmd[:cmd.index("tests/native_ehl8_client.c")] + [
            "-DEHL_CONNECT_TIMEOUT_MS=1100UL",
            "tests/native_ehl8_client.c", "-o", cls.short_connect_exe]
        subprocess.run(cmd_short, cwd=ROOT, check=True, timeout=45)

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

    async def test_host_native_clients_wait_for_delayed_server_start(self):
        """Actual TCP ECONNREFUSED must be recoverable during startup only."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port_number = probe.getsockname()[1]
        port = str(port_number)
        peers = []
        server = None
        try:
            for name, local_x, remote_x in (
                ("boot_A", "21", "34"), ("boot_B", "34", "21")
            ):
                peers.append(await asyncio.create_subprocess_exec(
                    self.exe, "127.0.0.1", port, "123456",
                    name, local_x, remote_x,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE))
            # Both C game clients start BEFORE server.listen(): the original
            # client would fail on the first refused connection.
            await asyncio.sleep(0.75)
            self.assertTrue(all(p.returncode is None for p in peers),
                            "native client exited before host server came online")
            server = server_module.SessionServer("123456", 2, idle_seconds=300)
            await server.start("127.0.0.1", port_number)
            outputs = await asyncio.wait_for(asyncio.gather(
                *(p.communicate() for p in peers)), timeout=12)
            # Each process only reports remote pose after PLAYING; the
            # server may already have returned to an empty room as they exit.
            for p, (stdout, stderr) in zip(peers, outputs):
                self.assertEqual(p.returncode, 0, stderr)
                self.assertIn(b"remote overworld pose verified", stdout)
        finally:
            for p in peers:
                if p.returncode is None:
                    p.kill()
                    await p.wait()
            if server is not None:
                await server.stop()

    async def test_permanently_unavailable_server_reaches_connect_deadline(self):
        """Bounded retries may not silently loop forever without a server."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = str(probe.getsockname()[1])
        p = await asyncio.create_subprocess_exec(
            self.short_connect_exe, "127.0.0.1", port, "123456",
            "no_host", "21", "34",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(p.communicate(), timeout=4)
            self.assertEqual(p.returncode, 4, (stdout, stderr))
        finally:
            if p.returncode is None:
                p.kill()
                await p.wait()

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

    async def test_two_native_clients_transition_maps_and_hide_reappear(self):
        """Actual C clients switch map ID, send inactive poses, then respawn.

        Uses production Python EHL8 relay, without any mock gameplay/save.
        The C peers assert BOTH sides receive each transition in sequence.
        """
        class PoseTrackingServer(server_module.SessionServer):
            def __init__(self):
                super().__init__("123456", 2, idle_seconds=300)
                self.pose_phases = {}

            async def process(self, peer, msg):
                if msg.kind == server_module.POSE and peer.stage == "GAME":
                    # Track the actual delivered wire values, not just
                    # the native client's final "success" text.
                    self.pose_phases.setdefault(peer.profile, set()).add(
                        (msg.payload[5], msg.payload[9]))
                await super().process(peer, msg)

        server = PoseTrackingServer()
        listener = await server.start("127.0.0.1", 0)
        port = str(listener.sockets[0].getsockname()[1])
        peers = []
        try:
            for identity, x, remote_x in (
                ("map_A", "21", "34"), ("map_B", "34", "21")
            ):
                peers.append(await asyncio.create_subprocess_exec(
                    self.exe, "127.0.0.1", port, "123456", identity,
                    x, remote_x, "mapcycle",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE))
            outputs = await asyncio.wait_for(asyncio.gather(
                *(peer.communicate() for peer in peers)), timeout=13)
            for peer, (stdout, stderr) in zip(peers, outputs):
                self.assertEqual(peer.returncode, 0, stderr)
                self.assertIn(b"native map transitions, inactive hide", stdout)
            for profile in (b"map_A", b"map_B"):
                phases = server.pose_phases.get(profile, set())
                for phase in ((1, 0), (1, 1), (0, 1), (1, 2)):
                    self.assertIn(phase, phases,
                                  f"{profile!r} did not send real pose {phase}")
        finally:
            for peer in peers:
                if peer.returncode is None:
                    peer.kill()
                    await peer.wait()
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
