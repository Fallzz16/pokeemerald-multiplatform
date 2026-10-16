"""M2.2 regression tests for the optional EHL8 resume protocol."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import emerald_session_server as S


class Reservations(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_mode_defaults_off(self):
        server = S.SessionServer("123456")
        self.assertFalse(server.resume_enabled)
        self.assertEqual(server.reservations, {})

    async def test_token_format_and_expiry(self):
        server = S.SessionServer("123456", resume_enabled=True)
        class Peer:
            def __init__(self):
                self.resume_token = None
                self.messages = []
            async def send(self, kind, payload, session):
                self.messages.append((kind, payload, session))
        peer = Peer()
        await server.issue_resume_token(peer)
        self.assertEqual(len(peer.resume_token), 32)
        self.assertEqual(peer.messages[0][0], S.RESUME)
        self.assertEqual(peer.messages[0][1], peer.resume_token)
