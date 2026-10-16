"""Real native C EHL8 game-client resume against the production Python server."""
import asyncio
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import emerald_session_server as S

ROOT = Path(__file__).resolve().parents[1]

class NativeResume(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = str(Path(cls.tmp.name) / "native_resume_client")
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

    async def test_native_recovers_real_socket_and_remote_pose(self):
        server = S.SessionServer("123456", 2, idle_seconds=120, resume_enabled=True)
        listener = await server.start("127.0.0.1", 0)
        port = str(listener.sockets[0].getsockname()[1])
        a = await asyncio.create_subprocess_exec(
            self.exe, "127.0.0.1", port, "123456", "trainer_A", "21", "34",
            "reconnect", stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        b = await asyncio.create_subprocess_exec(
            self.exe, "127.0.0.1", port, "123456", "trainer_B", "34", "21",
            "lingerlong", stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        try:
            for _ in range(200):
                if len(server.players) == 2 and all(
                        p.stage == "GAME" and p.resume_token for p in server.players.values()):
                    break
                await asyncio.sleep(.025)
            else:
                self.fail("native peers not ready: " + repr([(key, p.profile, p.stage, p.ready, bool(p.resume_token)) for key, p in server.players.items()]) + " reservations=" + repr(server.reservations) + " clients=" + repr((a.returncode, b.returncode)))
            await asyncio.sleep(.45)
            target = next(p for p in server.players.values() if p.profile == b"trainer_A")
            previous_slot = target.slot
            target.close()  # Simulated unexpected TCP interruption, NOT an admin kick.
            for _ in range(120):
                if previous_slot in server.reservations:
                    break
                await asyncio.sleep(.01)
            results = await asyncio.wait_for(asyncio.gather(
                a.communicate(), b.communicate()), 12)
            self.assertEqual(a.returncode, 0, results[0])
            self.assertEqual(b.returncode, 0, results[1])
            self.assertIn(b"token resume and fresh remote pose verified", results[0][0])
        finally:
            for proc in (a, b):
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
            await server.stop()

    async def test_native_legacy_client_server_compatibility(self):
        server = S.SessionServer("123456", 2, idle_seconds=120)
        listener = await server.start("127.0.0.1", 0)
        port = str(listener.sockets[0].getsockname()[1])
        a = await asyncio.create_subprocess_exec(
            self.exe, "127.0.0.1", port, "123456", "trainer_A", "21", "34",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        b = await asyncio.create_subprocess_exec(
            self.exe, "127.0.0.1", port, "123456", "trainer_B", "34", "21",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            outputs = await asyncio.wait_for(asyncio.gather(a.communicate(), b.communicate()), 13)
            self.assertEqual(a.returncode, 0, outputs[0])
            self.assertEqual(b.returncode, 0, outputs[1])
            self.assertIn(b"remote overworld pose verified", outputs[0][0])
            self.assertIn(b"remote overworld pose verified", outputs[1][0])
        finally:
            for proc in (a, b):
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
            await server.stop()
