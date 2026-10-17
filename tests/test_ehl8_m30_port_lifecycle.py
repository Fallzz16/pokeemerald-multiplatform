"""M3.0-A real-process smoke: server listen/exit/rebind, no saves or game involved."""
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tools" / "emerald_session_server.py"


class RealServerPortLifecycle(unittest.TestCase):
    def test_server_stops_and_same_port_can_be_reused(self):
        # Reserve a free loopback port and relinquish it before child bind.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        for iteration in range(3):
            child = subprocess.Popen(
                [sys.executable, str(SERVER), "--bind", "127.0.0.1",
                 "--port", str(port), "--pin-stdin", "--admin-stdin",
                 "--host-start", "--slots", "2", "--idle-minutes", "1"],
                cwd=ROOT, stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                child.stdin.write(b"123456\n")
                child.stdin.flush()
                # Connect to the real listener, without joining or sending PIN.
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    if child.poll() is not None:
                        self.fail(f"Real EHL8 server died before listening (attempt {iteration})")
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                            break
                    except OSError:
                        time.sleep(0.05)
                else:
                    self.fail(f"Real EHL8 server never bound loopback port (attempt {iteration})")
            finally:
                if child.poll() is None:
                    child.terminate()
                try:
                    child.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.communicate(timeout=5)
                if child.stdin and not child.stdin.closed:
                    child.stdin.close()
            # Rebind immediately; a lingering server or socket fails this gate.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind(("127.0.0.1", port))


if __name__ == "__main__":
    unittest.main()
