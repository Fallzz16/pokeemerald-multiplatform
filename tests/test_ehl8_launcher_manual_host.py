"""Real subprocess + real TCP integration of launcher-controlled M2.3 lobby.

Uses disposable session identities, loopback TCP and no Pokémon saves/game UI.
It DOES NOT certify graphical gameplay or a connection between physical PCs.
"""
import asyncio
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import emerald_launcher as L
import emerald_session_server as S


class LauncherHostProcessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "ehl8-live.log"
        self.writers = []
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as port_probe:
            port_probe.bind(("127.0.0.1", 0))
            self.port = port_probe.getsockname()[1]
        command = [sys.executable, "-u", str(ROOT / "tools" / "emerald_session_server.py"),
                   "--bind", "127.0.0.1", "--port", str(self.port),
                   "--slots", "2", "--pin-stdin", "--admin-stdin", "--resume-v1",
                   "--host-start", "--idle-minutes", "1"]
        with self.log.open("wb") as stream:
            self.server = subprocess.Popen(command, cwd=str(ROOT), stdin=subprocess.PIPE,
                                           stdout=stream, stderr=subprocess.STDOUT)
        L.deliver_pin_or_terminate(self.server, "123456", keep_open=True)
        for _ in range(100):
            if self.server.poll() is not None:
                self.fail("EHL8 server terminated during startup: " +
                          self.log.read_text(encoding="utf-8", errors="replace")[-900:])
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
                writer.close()
                await writer.wait_closed()
                break
            except OSError:
                await asyncio.sleep(0.05)
        else:
            self.fail("EHL8 server never started on loopback")

    async def asyncTearDown(self):
        for writer in self.writers:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass
        if self.server.poll() is None:
            self.server.terminate()
            try:
                self.server.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait(timeout=4)
        if self.server.stdin:
            self.server.stdin.close()
        self.tmp.cleanup()

    async def connect(self, name):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        self.writers.append(writer)
        async def send(kind, data=b"", session=0):
            writer.write(S.encode(S.Packet(kind, data, session)))
            await writer.drain()
        async def recv(expected):
            packet = await asyncio.wait_for(S.read_frame(reader), timeout=4)
            self.assertEqual(packet.kind, expected)
            return packet
        await send(S.HELLO)
        session = (await recv(S.WELCOME)).session
        await send(S.AUTH_PIN, b"123456", session)
        await recv(S.AUTH_PIN)
        await send(S.JOIN, name, session)
        await recv(S.JOIN)
        await recv(S.PLAYER_LIST)
        await recv(S.RESUME)  # resume-v1 token is sent before any READY
        return send, recv, session

    async def wait_gate(self, predicate):
        for _ in range(100):
            state = L.read_lobby_gate(self.log)
            if state is not None and predicate(state):
                return state
            await asyncio.sleep(0.05)
        self.fail("Lobby never reached expected state: " +
                  self.log.read_text(encoding="utf-8", errors="replace")[-1800:])

    async def test_two_real_tcp_clients_wait_for_launcher_start(self):
        send_a, recv_a, session_a = await self.connect(b"HOST_A")
        send_b, recv_b, session_b = await self.connect(b"GUEST_B")
        self.assertEqual(session_a, session_b)
        await recv_a(S.PLAYER_LIST)
        await send_a(S.READY, b"\x01", session_a)
        await recv_a(S.PLAYER_LIST)
        await recv_b(S.PLAYER_LIST)
        await send_b(S.READY, b"\x01", session_b)
        await recv_a(S.PLAYER_LIST)
        await recv_b(S.PLAYER_LIST)
        room = await self.wait_gate(lambda x: x["players"] == 2 and x["ready"] == 2)
        self.assertFalse(room["started"], "room started before host pressed START")
        await asyncio.sleep(0.15)
        self.assertFalse(L.read_lobby_gate(self.log)["started"])
        L.send_lobby_admin(self.server, "START")
        await recv_a(S.START)
        await recv_b(S.START)
        started = await self.wait_gate(lambda x: x["started"])
        self.assertEqual(started["players"], 2)


    async def test_two_clients_can_wait_over_30_seconds_before_host_start(self):
        """Real socket/heartbeat soak, not a graphical Emerald validation."""
        send_a, recv_a, session = await self.connect(b"WAIT_A")
        send_b, recv_b, session_b = await self.connect(b"WAIT_B")
        self.assertEqual(session_b, session)
        await recv_a(S.PLAYER_LIST)
        await send_a(S.READY, b"\x01", session)
        await recv_a(S.PLAYER_LIST)
        await recv_b(S.PLAYER_LIST)
        await send_b(S.READY, b"\x01", session)
        await recv_a(S.PLAYER_LIST)
        await recv_b(S.PLAYER_LIST)
        state = await self.wait_gate(lambda x: x["ready"] == 2)
        self.assertEqual(state["reserved"], 0)
        self.assertFalse(state["started"])
        # The native EHL8 client sends HEARTBEAT every ~10 seconds while
        # WAIT_START. Exercise the actual server's idle/session behavior.
        for _ in range(3):
            await asyncio.sleep(10.1)
            await send_a(S.HEARTBEAT, b"", session)
            await send_b(S.HEARTBEAT, b"", session)
            await recv_a(S.HEARTBEAT)
            await recv_b(S.HEARTBEAT)
            state = L.read_lobby_gate(self.log)
            self.assertEqual(state["players"], 2)
            self.assertEqual(state["ready"], 2)
            self.assertFalse(state["started"])
        L.send_lobby_admin(self.server, "START")
        await recv_a(S.START)
        await recv_b(S.START)
        self.assertTrue((await self.wait_gate(lambda x: x["started"]))["started"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
