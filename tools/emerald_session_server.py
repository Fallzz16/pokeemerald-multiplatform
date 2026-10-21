"""EHL8 dedicated *session* server, Windows-first. Does not execute Emerald.
IMPORTANT: the existing game's legacy Cable Club bytes cannot connect here.
Nothing in this process reads, writes or transports .sav files.
"""
from __future__ import annotations
import argparse
import asyncio
import ipaddress
import logging
import re
import secrets
import signal
import sys
import struct
import time
import threading
from dataclasses import dataclass

MAGIC = b"EHL8"
MAJOR, MINOR = 1, 0
HEADER = struct.Struct(">4sHHHHIQI")  # 28 bytes; network-order
MAX_PAYLOAD = 4096
HELLO, WELCOME, INCOMPATIBLE, AUTH_PIN, JOIN, PLAYER_LIST, READY, START, LEAVE, KICK, HEARTBEAT, POSE = range(1, 13)
PROFILE_ID = re.compile(rb"[A-Za-z0-9_-]{1,48}\Z")
READ_TIMEOUT = 35
# PIN failures are LAN-scoped, time-limited and memory-bounded.
PIN_FAILURE_WINDOW_SECONDS = 15 * 60
PIN_MAX_TRACKED_ADDRESSES = 256
PIN_MAX_FAILURES = 64
RESUME = 18  # Optional EHL8 type 18, no frame version change
RESUME_TOKEN_BYTES = 32
RESUME_HOLD_SECONDS = 60

class ProtocolError(Exception):
    pass

@dataclass(frozen=True)
class Packet:
    kind: int
    payload: bytes = b""
    session: int = 0
    request: int = 0

def encode(p: Packet) -> bytes:
    if not 1 <= p.kind <= 18 or len(p.payload) > MAX_PAYLOAD:
        raise ProtocolError("invalid outgoing message")
    return HEADER.pack(MAGIC, MAJOR, MINOR, p.kind, 0, len(p.payload), p.session, p.request) + p.payload

async def read_frame(reader: asyncio.StreamReader) -> Packet:
    magic, major, minor, kind, flags, size, session, request = HEADER.unpack(
        await reader.readexactly(HEADER.size))
    if (magic != MAGIC or (major, minor) != (MAJOR, MINOR) or flags != 0
            or not 1 <= kind <= 18 or size > MAX_PAYLOAD):
        raise ProtocolError("invalid or incompatible EHL8 frame")
    return Packet(kind, await reader.readexactly(size), session, request)

def valid_pose(p: bytes) -> bool:
    if len(p) != 18 or p[:5] != b"LANP\x01" or p[17] != 0:
        return False
    x, y = struct.unpack_from(">HH", p, 10)
    return (p[5] <= 1 and p[14] <= 4 and p[15] <= 1 and p[16] <= 15
            and x <= 2047 and y <= 2047 and (p[5] == 0 or p[14] > 0))

@dataclass(frozen=True)
class Reservation:
    profile: bytes
    token: bytes
    expires_at: float


class Peer:
    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.slot = None
        self.profile = None
        self.stage = "HELLO"
        self.ready = False
        self.last_pose = 0.0
        self.last_seq = None
        self.closed = False
        self.allow_resume = True
        self.resume_token = None
        self.last_heard = time.monotonic()
        self.address = writer.get_extra_info("peername")

    async def send(self, kind, data=b"", session=0, request=0):
        if self.closed:
            return
        self.writer.write(encode(Packet(kind, data, session, request)))
        if self.writer.transport.get_write_buffer_size() > 2 * (MAX_PAYLOAD + HEADER.size):
            raise ProtocolError("peer cannot keep up")
        await asyncio.wait_for(self.writer.drain(), 2)

    def close(self):
        self.closed = True
        self.writer.close()

class SessionServer:
    def __init__(self, pin: str, slots=2, idle_seconds=900,
                 resume_enabled=False, reservation_seconds=RESUME_HOLD_SECONDS,
                 manual_start=False):
        if not re.fullmatch(r"[0-9]{6}", pin) or not 1 <= slots <= 2:
            raise ValueError("PIN must be six digits; M2 currently supports 1-2 players")
        self.pin = pin.encode("ascii")
        self.slots = slots
        self.idle_seconds = idle_seconds
        self.session = secrets.randbits(64) or 1
        self.players = {}
        self.connected = set()
        # IP -> (failures in window, blocked_until, last_failure_monotonic)
        self.invalid_attempts = {}
        self.resume_enabled = bool(resume_enabled)
        if not 1 <= reservation_seconds <= 60:
            raise ValueError("resume reservation must be 1..60 seconds")
        self.reservation_seconds = reservation_seconds
        self.reservations = {}
        self.in_game = False
        self.locked = False
        self.manual_start = bool(manual_start)
        self.empty_since = time.monotonic()
        self.listener = None
        self.stopped = asyncio.Event()
        self.log = logging.getLogger("emerald.session")

    async def start(self, bind="127.0.0.1", port=45680):
        self.listener = await asyncio.start_server(self.handle, bind, port, limit=8192, backlog=8)
        self.log.info("EHL8 session listening on %s:%s (%s slots).",
                      bind, self.listener.sockets[0].getsockname()[1], self.slots)
        self.log.info("EHL8_ROOM_COUNT=%d/%d", len(self.players), self.slots)
        self.log.info("EHL8_ROOM_LOCKED=0")
        self.log.info("EHL8_READY_COUNT=0/%d", self.slots)
        self.log.info("EHL8_ROOM_STARTED=0")
        self.log_room_state()
        return self.listener

    async def stop(self):
        if self.listener is not None:
            self.listener.close()
            await self.listener.wait_closed()
            self.listener = None
        for peer in tuple(self.connected):
            peer.allow_resume = False
            peer.close()
        self.reservations.clear()
        self.stopped.set()

    async def sweep(self):
        while not self.stopped.is_set():
            await asyncio.sleep(1)
            self.expire_reservations()
            if not self.connected and not self.players and not self.reservations and time.monotonic() - self.empty_since >= self.idle_seconds:
                self.log.info("Empty session timed out")
                await self.stop()
                return
            for peer in tuple(self.connected):
                if time.monotonic() - peer.last_heard > READ_TIMEOUT + 5:
                    peer.close()

    def expire_reservations(self):
        now = time.monotonic()
        expired = [slot for slot, hold in self.reservations.items()
                   if hold.expires_at <= now]
        for slot in expired:
            del self.reservations[slot]
            self.log.info("EHL8_RESERVATION_EXPIRED=1")
        if expired:
            self.log.info("EHL8_ROOM_RESERVED=%d/%d",
                          len(self.reservations), self.slots)
        room_ended = not self.players and not self.reservations and self.in_game
        if room_ended:
            self.in_game = False
            self.log.info("EHL8_ROOM_STARTED=0")
        if expired or room_ended:
            self.log_room_state()

    async def issue_resume_token(self, peer):
        peer.resume_token = secrets.token_bytes(RESUME_TOKEN_BYTES)
        await peer.send(RESUME, peer.resume_token, self.session)

    def log_room_state(self):
        """One complete state record for the GUI; never includes PIN or saves."""
        self.log.info("EHL8_ROOM_STATE=%d/%d,%d/%d,%d,%d/%d",
                      len(self.players), self.slots,
                      sum(peer.ready for peer in self.players.values()), self.slots,
                      int(self.in_game), len(self.reservations), self.slots)

    def log_ready_count(self):
        self.log.info("EHL8_READY_COUNT=%d/%d",
                      sum(peer.ready for peer in self.players.values()), self.slots)
        self.log_room_state()

    async def start_ready_room(self):
        # READY remains a native client acknowledgement; only the local host
        # can authorize START when --host-start is enabled.
        if (self.in_game or len(self.players) != self.slots or
            self.reservations or not all(
                peer.ready and peer.stage == "LOBBY"
                for peer in self.players.values())):
            return False
        self.in_game = True
        for peer in self.players.values():
            peer.stage = "GAME"
        self.log.info("EHL8_ROOM_STARTED=1")
        self.log_room_state()
        await self.broadcast(START, b"")
        return True

    async def admin_command(self, command):
        """Private stdin-only administration; never an EHL8 network message."""
        if command == "START" and self.manual_start:
            started = await self.start_ready_room()
            self.log.info("EHL8_ADMIN_START_OK=%d", int(started))
            return started
        if command == "LOCK ON":
            self.locked = True
            self.log.info("EHL8_ROOM_LOCKED=1")
            return True
        if command == "LOCK OFF":
            self.locked = False
            self.log.info("EHL8_ROOM_LOCKED=0")
            return True
        if command.startswith("DROP ") and self.resume_enabled:
            # Local QA-only transport interruption; preserve the recoverable token.
            identity = command[5:].encode("ascii", errors="ignore")
            if not PROFILE_ID.fullmatch(identity):
                return False
            peer = next((p for p in self.players.values()
                         if p.profile == identity and p.stage == "GAME"), None)
            if peer is None:
                self.log.info("EHL8_ADMIN_DROP_OK=0")
                return False
            peer.close()
            self.log.info("EHL8_ADMIN_DROP_OK=1")
            return True
        if command.startswith("KICK "):
            identity = command[5:].encode("ascii", errors="ignore")
            if not PROFILE_ID.fullmatch(identity):
                return False
            peer = next((p for p in self.players.values() if p.profile == identity), None)
            if peer is None:
                held_slot = next(
                    (slot for slot, hold in self.reservations.items()
                     if hold.profile == identity), None)
                if held_slot is None:
                    self.log.info("EHL8_ADMIN_KICK_OK=0")
                    return False
                del self.reservations[held_slot]
                self.log.info("EHL8_ROOM_RESERVED=%d/%d",
                              len(self.reservations), self.slots)
                self.log.info("EHL8_ADMIN_KICK_OK=1")
                self.log_room_state()
                self.expire_reservations()
                return True
            peer.allow_resume = False
            try:
                await peer.send(KICK, b"Removed by host", self.session)
            except (OSError, ConnectionError, asyncio.TimeoutError, ProtocolError):
                pass
            peer.close()
            self.log.info("EHL8_ADMIN_KICK_OK=1")
            return True
        return False

    def snapshot(self):
        data = bytearray([len(self.players)])
        for slot, peer in sorted(self.players.items()):
            name = peer.profile or b""
            data += bytes([slot, int(peer.ready), len(name)]) + name
        return bytes(data)

    async def broadcast(self, kind, data, exclude=None):
        for peer in tuple(self.players.values()):
            if peer is exclude:
                continue
            try:
                await peer.send(kind, data, self.session)
            except (OSError, ConnectionError, asyncio.TimeoutError, ProtocolError):
                peer.close()

    def _prune_pin_failures(self, now):
        """Forget stale addresses, but never clear an active cooldown."""
        for address, (_, blocked_until, last_failed) in tuple(self.invalid_attempts.items()):
            if (blocked_until <= now and
                    now - last_failed >= PIN_FAILURE_WINDOW_SECONDS):
                del self.invalid_attempts[address]

    def _allow_pin_address(self, address, now):
        """Keep the LAN PIN limiter bounded without evicting active cooldowns."""
        self._prune_pin_failures(now)
        if address in self.invalid_attempts or len(self.invalid_attempts) < PIN_MAX_TRACKED_ADDRESSES:
            return True
        # Evict only the oldest address whose cooldown has ended. If all
        # tracked addresses are still blocked, refuse untracked connections.
        available = ((entry[2], ip) for ip, entry in self.invalid_attempts.items()
                     if entry[1] <= now)
        oldest = min(available, default=None)
        if oldest is None:
            return False
        del self.invalid_attempts[oldest[1]]
        return True

    def _record_invalid_pin(self, address, now):
        failures, _, last_failed = self.invalid_attempts.get(address, (0, 0.0, 0.0))
        if now - last_failed >= PIN_FAILURE_WINDOW_SECONDS:
            failures = 0
        failures = min(failures + 1, PIN_MAX_FAILURES)
        blocked_until = (now + min(300, 10 * 2 ** min(failures, 5))
                         if failures >= 3 else 0.0)
        self.invalid_attempts[address] = (failures, blocked_until, now)

    async def handle(self, reader, writer):
        peer = Peer(reader, writer)
        address = peer.address[0] if peer.address else "unknown"
        now = time.monotonic()
        if not self._allow_pin_address(address, now):
            writer.close()
            return
        _, blocked_until, _ = self.invalid_attempts.get(address, (0, 0.0, 0.0))
        if blocked_until > now or len(self.connected) >= self.slots + 8:
            writer.close()
            return
        self.connected.add(peer)
        try:
            while not peer.closed:
                try:
                    msg = await asyncio.wait_for(read_frame(reader), READ_TIMEOUT)
                except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionResetError):
                    break
                peer.last_heard = time.monotonic()
                await self.process(peer, msg)
        except (ProtocolError, OSError, ConnectionError) as ex:
            if isinstance(ex, ProtocolError):
                peer.allow_resume = False  # invalid traffic never reserves a slot
            self.log.debug("Session peer dropped: %s", ex)
        finally:
            if peer.slot is not None and self.players.get(peer.slot) is peer:
                del self.players[peer.slot]
                if (self.resume_enabled and peer.allow_resume and
                    peer.stage == "GAME" and peer.resume_token is not None and
                    not self.stopped.is_set()):
                    self.reservations[peer.slot] = Reservation(
                        peer.profile, peer.resume_token,
                        time.monotonic() + self.reservation_seconds)
                    self.log.info("EHL8_ROOM_RESERVED=%d/%d",
                                  len(self.reservations), self.slots)
                self.log.info("EHL8_ROOM_COUNT=%d/%d", len(self.players), self.slots)
                self.log_ready_count()
                if self.players:
                    await self.broadcast(LEAVE, bytes([peer.slot]))
                    await self.broadcast(PLAYER_LIST, self.snapshot())
                elif not self.reservations:
                    self.in_game = False
                    self.log.info("EHL8_ROOM_STARTED=0")
                    self.log_room_state()
            peer.close()
            self.connected.discard(peer)
            if not self.players and not self.connected:
                self.empty_since = time.monotonic()
            try:
                await writer.wait_closed()
            except (OSError, ConnectionError):
                pass

    async def process(self, peer, msg):
        if peer.stage == "HELLO":
            if msg.kind != HELLO or msg.payload or msg.session:
                raise ProtocolError("HELLO expected")
            await peer.send(WELCOME, bytes([self.slots]), self.session, msg.request)
            peer.stage = "AUTH"
            return
        if peer.stage == "AUTH":
            if msg.kind != AUTH_PIN or len(msg.payload) != 6:
                raise ProtocolError("six-digit PIN expected")
            ip = peer.address[0] if peer.address else "unknown"
            # Already-open connections must not bypass a cooldown triggered
            # by another connection from the same address.
            _, blocked_until, _ = self.invalid_attempts.get(ip, (0, 0.0, 0.0))
            if blocked_until > time.monotonic():
                await peer.send(KICK, b"PIN cooldown active", self.session)
                raise ProtocolError("PIN cooldown active")
            if not secrets.compare_digest(msg.payload, self.pin):
                now = time.monotonic()
                # Multiple connections can finish AUTH after passing handle's
                # capacity gate. Enforce the bound again before recording.
                if self._allow_pin_address(ip, now):
                    self._record_invalid_pin(ip, now)
                await peer.send(KICK, b"Invalid PIN", self.session)
                raise ProtocolError("invalid PIN")
            # A valid PIN resets prior typos without weakening active bans:
            # handle() rejects an address until its cooldown has ended.
            ip = peer.address[0] if peer.address else "unknown"
            self.invalid_attempts.pop(ip, None)
            peer.stage = "JOIN"
            await peer.send(AUTH_PIN, b"\x01", self.session, msg.request)
            return
        if msg.session != self.session:
            raise ProtocolError("invalid session id")
        if peer.stage == "JOIN":
            self.expire_reservations()
            if msg.kind == RESUME and self.resume_enabled:
                identity, sep, token = msg.payload.partition(b"\0")
                held_slot = next(
                    (slot for slot, hold in self.reservations.items()
                     if hold.profile == identity), None)
                hold = self.reservations.get(held_slot)
                if (not sep or not PROFILE_ID.fullmatch(identity) or
                    len(token) != RESUME_TOKEN_BYTES or hold is None or
                    not secrets.compare_digest(token, hold.token) or
                    hold.expires_at <= time.monotonic()):
                    await peer.send(KICK, b"Invalid resume credentials", self.session)
                    raise ProtocolError("invalid resume credentials")
                del self.reservations[held_slot]
                peer.slot, peer.profile, peer.stage, peer.ready = (
                    held_slot, identity, "GAME", True)
                self.players[held_slot] = peer
                self.log.info("EHL8_ROOM_COUNT=%d/%d", len(self.players), self.slots)
                self.log.info("EHL8_ROOM_RESERVED=%d/%d",
                              len(self.reservations), self.slots)
                self.log.info("EHL8_RESUMED=1")
                self.log_ready_count()
                await peer.send(JOIN, bytes([held_slot]), self.session, msg.request)
                await self.broadcast(PLAYER_LIST, self.snapshot())
                await peer.send(START, b"", self.session)
                await self.issue_resume_token(peer)
                return
            if msg.kind != JOIN or not PROFILE_ID.fullmatch(msg.payload):
                raise ProtocolError("invalid profile identity")
            if self.locked:
                await peer.send(KICK, b"Lobby locked", self.session)
                raise ProtocolError("lobby locked")
            if (any(p.profile == msg.payload for p in self.players.values()) or
                any(hold.profile == msg.payload for hold in self.reservations.values())):
                await peer.send(KICK, b"Profile already active", self.session)
                raise ProtocolError("duplicate identity")
            free = next(
                (slot for slot in range(1, self.slots + 1)
                 if slot not in self.players and slot not in self.reservations),
                None)
            if free is None:
                await peer.send(KICK, b"Lobby full", self.session)
                raise ProtocolError("session full")
            peer.slot, peer.profile = free, msg.payload
            peer.stage = "GAME" if self.in_game else "LOBBY"
            self.players[free] = peer
            self.log.info("EHL8_ROOM_COUNT=%d/%d", len(self.players), self.slots)
            self.log_ready_count()
            await peer.send(JOIN, bytes([free]), self.session, msg.request)
            await self.broadcast(PLAYER_LIST, self.snapshot())
            if self.resume_enabled:
                await self.issue_resume_token(peer)
            if self.in_game:
                await peer.send(START, b"", self.session)
            return
        # A READY=0 queued just before the host's START can arrive just
        # AFTER START. It is an old lobby CANCEL, not malicious gameplay data.
        # Do NOT evict a player or retroactively cancel an active session.
        # A late joiner still acknowledges JOIN with READY=1 as usual.
        if msg.kind == READY and peer.stage == "GAME":
            if msg.payload not in (b"\x00", b"\x01"):
                raise ProtocolError("invalid ready acknowledgement in running room")
            if msg.payload == b"\x00":
                return
            if not peer.ready:
                peer.ready = True
                self.log_ready_count()
                await self.broadcast(PLAYER_LIST, self.snapshot())
            return
        if msg.kind == HEARTBEAT:
            await peer.send(HEARTBEAT, b"", self.session, msg.request)
            return
        if msg.kind == LEAVE:
            peer.allow_resume = False
            peer.close()
            return
        if msg.kind == READY and peer.stage == "LOBBY":
            if msg.payload not in (b"\x00", b"\x01"):
                raise ProtocolError("invalid ready state")
            peer.ready = msg.payload == b"\x01"
            self.log_ready_count()
            await self.broadcast(PLAYER_LIST, self.snapshot())
            if not self.manual_start:
                await self.start_ready_room()
            return
        if msg.kind == POSE and peer.stage == "GAME":
            if not valid_pose(msg.payload):
                raise ProtocolError("invalid LANP packet")
            now = time.monotonic()
            if now - peer.last_pose < 0.055:
                return  # <= ~18 poses per sec/peer, default sender ~10 Hz
            seq = int.from_bytes(msg.payload[6:8], "big")
            if peer.last_seq is not None and not (0 < (seq - peer.last_seq) % 65536 < 32768):
                return  # discard stale/replayed
            peer.last_pose, peer.last_seq = now, seq
            await self.broadcast(POSE, bytes([peer.slot]) + msg.payload, exclude=peer)
            return
        raise ProtocolError("message invalid in current state")

async def serve(args):
    session = SessionServer(args.pin, args.slots, args.idle_minutes * 60,
                            resume_enabled=args.resume_v1,
                            manual_start=args.host_start)
    await session.start(args.bind, args.port)
    loop = asyncio.get_running_loop()
    if args.admin_stdin:
        def private_stdin_commands():
            while True:
                line = sys.stdin.readline(64)
                if not line:
                    return
                command = line.strip()
                if command not in ("LOCK ON", "LOCK OFF", "START") and not re.fullmatch(
                        r"(KICK|DROP) [A-Za-z0-9_-]{1,48}", command):
                    continue
                try:
                    loop.call_soon_threadsafe(
                        lambda value=command: asyncio.create_task(session.admin_command(value)))
                except RuntimeError:
                    return
        threading.Thread(target=private_stdin_commands, name="EHL8-LocalAdmin",
                         daemon=True).start()
    for name in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, name), lambda: asyncio.create_task(session.stop()))
        except (RuntimeError, NotImplementedError):
            pass
    task = asyncio.create_task(session.sweep())
    try:
        await session.stopped.wait()
    finally:
        task.cancel()
        await session.stop()

def main():
    parser = argparse.ArgumentParser(description="Emerald EHL8 LAN dedicated server (game adapter not implemented yet)")
    parser.add_argument("--bind", default="127.0.0.1", help="Localhost by default. Use 0.0.0.0 only on trusted private LAN.")
    parser.add_argument("--port", type=int, default=45680)
    credentials = parser.add_mutually_exclusive_group(required=True)
    credentials.add_argument("--pin", help="Legacy CLI 6-digit PIN (visible in process arguments)")
    credentials.add_argument("--pin-stdin", action="store_true",
                             help="Read 6-digit PIN from stdin so it is not exposed in the command line")
    parser.add_argument("--host-start", action="store_true",
                        help="Require local administrator START after both clients READY")
    parser.add_argument("--resume-v1", action="store_true",
                        help="Opt-in type 18 resume tokens; requires an updated client")
    parser.add_argument("--admin-stdin", action="store_true",
                        help="Private lobby commands via stdin; requires --pin-stdin")
    parser.add_argument("--slots", type=int, choices=(1, 2), default=2)
    parser.add_argument("--idle-minutes", type=int, default=15)
    args = parser.parse_args()
    if args.admin_stdin and not args.pin_stdin:
        parser.error("--admin-stdin requires --pin-stdin")
    if args.host_start and not args.admin_stdin:
        parser.error("--host-start requires --admin-stdin")
    try:
        ipaddress.IPv4Address(args.bind)
    except ipaddress.AddressValueError:
        parser.error("bind must be a numeric IPv4 address")
    if not 1 <= args.port <= 65534 or not 1 <= args.idle_minutes <= 1440:
        parser.error("port or idle minutes out of range")
    if args.pin_stdin:
        args.pin = sys.stdin.readline(16).strip()
    if not re.fullmatch(r"[0-9]{6}", args.pin or ""):
        parser.error("PIN must contain exactly six digits")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(serve(args))
    except OSError as ex:
        parser.exit(2, f"Could not open session listener: {ex}\n")

if __name__ == "__main__":
    main()
