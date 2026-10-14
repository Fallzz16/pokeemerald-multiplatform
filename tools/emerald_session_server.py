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
from dataclasses import dataclass

MAGIC = b"EHL8"
MAJOR, MINOR = 1, 0
HEADER = struct.Struct(">4sHHHHIQI")  # 28 bytes; network-order
MAX_PAYLOAD = 4096
HELLO, WELCOME, INCOMPATIBLE, AUTH_PIN, JOIN, PLAYER_LIST, READY, START, LEAVE, KICK, HEARTBEAT, POSE = range(1, 13)
PROFILE_ID = re.compile(rb"[A-Za-z0-9_-]{1,48}\Z")
READ_TIMEOUT = 35
RECONNECT_GRACE_SECONDS = 60

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
        self.graceful_leave = False
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
    def __init__(self, pin: str, slots=2, idle_seconds=900):
        if not re.fullmatch(r"[0-9]{6}", pin) or not 1 <= slots <= 2:
            raise ValueError("PIN must be six digits; M2 currently supports 1-2 players")
        self.pin = pin.encode("ascii")
        self.slots = slots
        self.idle_seconds = idle_seconds
        self.session = secrets.randbits(64) or 1
        self.players = {}
        # Profile ID -> (slot, expiry), for transient network loss only.
        # Reservations contain no save data, PIN or IP information.
        self.reservations = {}
        self.connected = set()
        self.invalid_attempts = {}  # IP -> (failure count, blocked_until)
        self.in_game = False
        self.empty_since = time.monotonic()
        self.listener = None
        self.stopped = asyncio.Event()
        self.log = logging.getLogger("emerald.session")

    async def start(self, bind="127.0.0.1", port=45680):
        self.listener = await asyncio.start_server(self.handle, bind, port, limit=8192, backlog=8)
        self.log.info("EHL8 session listening on %s:%s (%s slots).",
                      bind, self.listener.sockets[0].getsockname()[1], self.slots)
        self.log.info("EHL8_ROOM_COUNT=%d/%d", len(self.players), self.slots)
        return self.listener

    async def stop(self):
        if self.listener is not None:
            self.listener.close()
            await self.listener.wait_closed()
            self.listener = None
        for peer in tuple(self.connected):
            peer.close()
        self.stopped.set()

    def expire_reservations(self):
        now = time.monotonic()
        expired = [profile for profile, (_, until) in self.reservations.items()
                   if until <= now]
        for profile in expired:
            del self.reservations[profile]
        if not self.players and not self.reservations:
            if expired:
                # Start idle-timeout *after* the final 60s grace expires,
                # not from startup or from the last active game frame.
                self.empty_since = now
            self.in_game = False
        return len(expired)

    async def sweep(self):
        while not self.stopped.is_set():
            await asyncio.sleep(1)
            self.expire_reservations()
            if (not self.connected and not self.players and not self.reservations and
                    time.monotonic() - self.empty_since >= self.idle_seconds):
                self.log.info("Empty session timed out")
                await self.stop()
                return
            for peer in tuple(self.connected):
                if time.monotonic() - peer.last_heard > READ_TIMEOUT + 5:
                    peer.close()

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

    async def handle(self, reader, writer):
        peer = Peer(reader, writer)
        address = peer.address[0] if peer.address else "unknown"
        failures, blocked_until = self.invalid_attempts.get(address, (0, 0.0))
        if blocked_until > time.monotonic() or len(self.connected) >= self.slots + 8:
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
            self.log.debug("Session peer dropped: %s", ex)
        finally:
            if peer.slot is not None and self.players.get(peer.slot) is peer:
                del self.players[peer.slot]
                if (not peer.graceful_leave and not self.stopped.is_set()
                        and peer.profile is not None):
                    self.reservations[peer.profile] = (
                        peer.slot, time.monotonic() + RECONNECT_GRACE_SECONDS)
                    self.log.info("EHL8_SLOT_RESERVED=%d/60", peer.slot)
                self.log.info("EHL8_ROOM_COUNT=%d/%d", len(self.players), self.slots)
                if self.players:
                    await self.broadcast(LEAVE, bytes([peer.slot]))
                    await self.broadcast(PLAYER_LIST, self.snapshot())
                else:
                    if not self.reservations:
                        self.in_game = False
            peer.close()
            self.connected.discard(peer)
            if not self.players and not self.reservations and not self.connected:
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
            if not secrets.compare_digest(msg.payload, self.pin):
                ip = peer.address[0] if peer.address else "unknown"
                failures, until = self.invalid_attempts.get(ip, (0, 0.0))
                # Failure count is retained even before cooldown begins; never
                # reset on the second wrong PIN by treating until=0 as expiry.
                failures += 1
                self.invalid_attempts[ip] = (
                    failures,
                    time.monotonic() + min(300, 10 * 2 ** min(failures, 5))
                    if failures >= 3 else 0.0)
                await peer.send(KICK, b"Invalid PIN", self.session)
                raise ProtocolError("invalid PIN")
            peer.stage = "JOIN"
            await peer.send(AUTH_PIN, b"\x01", self.session, msg.request)
            return
        if msg.session != self.session:
            raise ProtocolError("invalid session id")
        if peer.stage == "JOIN":
            if msg.kind != JOIN or not PROFILE_ID.fullmatch(msg.payload):
                raise ProtocolError("invalid profile identity")
            if any(p.profile == msg.payload for p in self.players.values()):
                await peer.send(KICK, b"Profile already active", self.session)
                raise ProtocolError("duplicate identity")
            self.expire_reservations()
            reserved = self.reservations.get(msg.payload)
            if reserved is not None:
                free = reserved[0]
                if free in self.players:
                    raise ProtocolError("reserved slot already occupied")
                del self.reservations[msg.payload]
                self.log.info("EHL8_SLOT_RECLAIMED=%d", free)
            else:
                held = {slot for slot, _ in self.reservations.values()}
                free = next((slot for slot in range(1, self.slots + 1)
                             if slot not in self.players and slot not in held), None)
            if free is None:
                await peer.send(KICK, b"Lobby full", self.session)
                raise ProtocolError("session full")
            peer.slot, peer.profile = free, msg.payload
            peer.stage = "GAME" if self.in_game else "LOBBY"
            self.players[free] = peer
            self.log.info("EHL8_ROOM_COUNT=%d/%d", len(self.players), self.slots)
            await peer.send(JOIN, bytes([free]), self.session, msg.request)
            await self.broadcast(PLAYER_LIST, self.snapshot())
            if self.in_game:
                await peer.send(START, b"", self.session)
            return
        # A late joiner receives START immediately in a running room.
        # The native SessionClient sends READY after JOIN regardless of room
        # state. Treat this final READY as an idempotent acknowledgement;
        # otherwise a replacement player disconnects on entering mid-game.
        if msg.kind == READY and peer.stage == "GAME":
            if msg.payload != b"\x01":
                raise ProtocolError("invalid ready acknowledgement in running room")
            if not peer.ready:
                peer.ready = True
                await self.broadcast(PLAYER_LIST, self.snapshot())
            return
        if msg.kind == HEARTBEAT:
            await peer.send(HEARTBEAT, b"", self.session, msg.request)
            return
        if msg.kind == LEAVE:
            peer.graceful_leave = True
            peer.close()
            return
        if msg.kind == READY and peer.stage == "LOBBY":
            if msg.payload not in (b"\x00", b"\x01"):
                raise ProtocolError("invalid ready state")
            peer.ready = msg.payload == b"\x01"
            await self.broadcast(PLAYER_LIST, self.snapshot())
            if len(self.players) == self.slots and all(p.ready for p in self.players.values()):
                self.in_game = True
                for p in self.players.values():
                    p.stage = "GAME"
                await self.broadcast(START, b"")
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
    session = SessionServer(args.pin, args.slots, args.idle_minutes * 60)
    await session.start(args.bind, args.port)
    loop = asyncio.get_running_loop()
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
    parser.add_argument("--slots", type=int, choices=(1, 2), default=2)
    parser.add_argument("--idle-minutes", type=int, default=15)
    args = parser.parse_args()
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
