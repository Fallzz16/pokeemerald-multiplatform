"""EHL8 protocol-only functional QA: 50 disposable identities in 25 pairs.

Never opens a game, never creates/reads/writes .sav files. Binds/connects only
IPv4 localhost. NOT a benchmark for 50 simultaneous players or game FPS.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import struct
import sys
import time

HEADER = struct.Struct('>4sHHHHIQI')
MAGIC = b'EHL8'
MAJOR, MINOR = 1, 0
MAX_PAYLOAD = 4096
HELLO, WELCOME, INCOMPATIBLE, AUTH_PIN, JOIN, PLAYER_LIST, READY, START, LEAVE, KICK, HEARTBEAT, POSE = range(1, 13)

class EHL8Error(RuntimeError):
    pass

@dataclass
class Frame:
    kind: int
    payload: bytes = b''
    session: int = 0
    request: int = 0


def encode(frame: Frame) -> bytes:
    if frame.kind not in range(1, 13) or len(frame.payload) > MAX_PAYLOAD:
        raise EHL8Error('Invalid outgoing EHL8 frame')
    return HEADER.pack(MAGIC, MAJOR, MINOR, frame.kind, 0, len(frame.payload),
                       frame.session, frame.request) + frame.payload


def exact(sock: socket.socket, length: int) -> bytes:
    out = bytearray()
    while len(out) < length:
        chunk = sock.recv(length - len(out))
        if not chunk:
            raise EHL8Error('Connection closed before complete frame')
        out.extend(chunk)
    return bytes(out)


def receive(sock: socket.socket) -> Frame:
    magic, major, minor, kind, flags, length, session, request = HEADER.unpack(exact(sock, HEADER.size))
    if (magic != MAGIC or (major, minor) != (MAJOR, MINOR) or flags or
            kind not in range(1, 13) or length > MAX_PAYLOAD):
        raise EHL8Error('Invalid EHL8 response header')
    return Frame(kind, exact(sock, length), session, request)


def pose(seq: int, x: int, y: int) -> bytes:
    if not (0 <= seq <= 65535 and 0 <= x <= 2047 and 0 <= y <= 2047):
        raise ValueError('Invalid pose coordinates or sequence')
    # LANP v1: 18 bytes. Never includes save/trainer identifiers.
    return b'LANP\x01' + b'\x01' + struct.pack('>H', seq) + b'\x00\x01' + struct.pack('>HH', x, y) + bytes([1, 0, 1, 0])


class Bot:
    def __init__(self, host: str, port: int, pin: str, name: str, timeout: float):
        if host != '127.0.0.1':
            raise ValueError('Bots are restricted to 127.0.0.1 by design')
        if not (1 <= port <= 65534) or len(pin) != 6 or not pin.isascii() or not pin.isdecimal():
            raise ValueError('Invalid port or PIN')
        if not name.startswith('QA_') or not name[3:].replace('_', '').isalnum() or len(name) > 48:
            raise ValueError('Invalid disposable identity')
        self.host, self.port, self.pin = host, port, pin
        self.name, self.timeout = name, timeout
        self.socket: socket.socket | None = None
        self.session = 0
        self.slot = 0
        self.latency_ms = 0.0
        self.request = 1

    def send(self, kind: int, payload: bytes = b'') -> None:
        if self.socket is None:
            raise EHL8Error('Not connected')
        self.socket.sendall(encode(Frame(kind, payload, self.session, self.request)))
        self.request += 1

    def until(self, kind: int, limit: int = 15) -> Frame:
        if self.socket is None:
            raise EHL8Error('Not connected')
        for _ in range(limit):
            result = receive(self.socket)
            if result.kind == KICK:
                raise EHL8Error('Server rejected QA identity: ' + result.payload.decode('utf-8', 'replace')[:80])
            if result.session != self.session:
                raise EHL8Error('Session changed unexpectedly')
            if result.kind == kind:
                return result
        raise EHL8Error('Expected EHL8 message not received: ' + str(kind))

    def connect(self):
        before = time.monotonic()
        self.socket = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.socket.settimeout(self.timeout)
        self.send(HELLO)
        response = receive(self.socket)
        if response.kind != WELCOME or response.session == 0 or response.payload != b'\x02':
            raise EHL8Error('Server not compatible with 2-slot EHL8')
        self.session = response.session
        self.latency_ms = round((time.monotonic() - before) * 1000, 2)
        self.send(AUTH_PIN, self.pin.encode('ascii'))
        if self.until(AUTH_PIN).payload != b'\x01':
            raise EHL8Error('PIN was not authenticated')
        self.send(JOIN, self.name.encode('ascii'))
        joined = self.until(JOIN)
        if len(joined.payload) != 1 or joined.payload[0] not in (1, 2):
            raise EHL8Error('Invalid slot assignment')
        self.slot = joined.payload[0]
        self.send(READY, b'\x01')

    def close(self):
        if self.socket is not None:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.socket.close()
            self.socket = None


def exercise_pair(host: str, port: int, pin: str, a_name: str, b_name: str, timeout: float) -> dict:
    a, b = Bot(host, port, pin, a_name, timeout), Bot(host, port, pin, b_name, timeout)
    try:
        a.connect()
        b.connect()
        if a.slot == b.slot:
            raise EHL8Error('Two identities received the same slot')
        a.until(START)
        b.until(START)
        # Test both movements and both directions; the production EHL8 server
        # limits poses to about 18 Hz, so send only one per client.
        started = time.monotonic()
        a.send(POSE, pose(1, 21, 22))
        rx = b.until(POSE)
        if rx.payload != bytes([a.slot]) + pose(1, 21, 22):
            raise EHL8Error('Corrupted A -> B movement relay')
        relay_a_ms = round((time.monotonic() - started) * 1000, 2)
        started = time.monotonic()
        b.send(POSE, pose(2, 23, 24))
        rx = a.until(POSE)
        if rx.payload != bytes([b.slot]) + pose(2, 23, 24):
            raise EHL8Error('Corrupted B -> A movement relay')
        relay_b_ms = round((time.monotonic() - started) * 1000, 2)
        # Clean up A and wait for B's LEAVE to ensure the server has freed its
        # slot. B stays in the GAME stage; rejoining must not reset the room.
        a.send(LEAVE)
        a.close()
        left = b.until(LEAVE)
        if left.payload != bytes([a.slot]):
            raise EHL8Error('Wrong slot in leave notification')
        fresh = Bot(host, port, pin, a_name, timeout)
        try:
            fresh.connect()
            if fresh.slot != a.slot:
                raise EHL8Error('Rejoining did not reclaim the available slot')
            fresh.until(START)
            # Replacement receives START immediately, independent of READY.
            fresh.send(POSE, pose(3, 25, 26))
            if b.until(POSE).payload != bytes([fresh.slot]) + pose(3, 25, 26):
                raise EHL8Error('No movement after rejoining')
        finally:
            fresh.close()
        return {'accounts': [a_name, b_name], 'join_ms': [a.latency_ms, b.latency_ms],
                'relay_ms': [relay_a_ms, relay_b_ms], 'rejoin': True}
    finally:
        a.close()
        b.close()


def run_suite(host: str, port: int, pin: str, cycles: int = 25, timeout: float = 4.0,
              progress=None) -> dict:
    if not (1 <= cycles <= 25):
        raise ValueError('Use 1..25 rounds (max 50 test identities)')
    started = time.monotonic()
    results = []
    errors = []
    for index in range(cycles):
        # New, distinct identity for each round. They are network names only:
        # never game accounts and never real .sav profiles.
        names = (f'QA_{index*2+1:03d}', f'QA_{index*2+2:03d}')
        try:
            result = exercise_pair(host, port, pin, names[0], names[1], timeout)
            result['round'] = index + 1
            results.append(result)
            if progress:
                progress(f'Rodada {index+1}/{cycles}: OK')
        except (EHL8Error, OSError, TimeoutError, ValueError) as ex:
            errors.append({'round': index + 1, 'accounts': list(names), 'error': str(ex)[:240]})
            if progress:
                progress(f'Rodada {index+1}/{cycles}: FALHA ({str(ex)[:90]})')
            # Continue to gather actionable failure counts in remaining rounds.
            time.sleep(0.08)
        # Server cleanup happens asynchronously after the peer closes. Avoid
        # interpreting an old slot not yet released as a new pair failure.
        time.sleep(0.06)
    latencies = [v for r in results for v in r['join_ms']]
    relays = [v for r in results for v in r['relay_ms']]
    return {'schema': 1, 'suite': 'EHL8_local_2_slots', 'tested_at': datetime.now(timezone.utc).isoformat(),
            'rounds_requested': cycles, 'rounds_passed': len(results), 'rounds_failed': len(errors),
            'identities_attempted': cycles * 2, 'max_concurrent_clients': 2,
            'avg_join_ms': round(sum(latencies) / len(latencies), 2) if latencies else None,
            'avg_relay_ms': round(sum(relays) / len(relays), 2) if relays else None,
            'rounds': results, 'errors': errors, 'elapsed_seconds': round(time.monotonic() - started, 2),
            'note': 'Protocol-only clients: no Emerald gameplay, no saves, no 50 concurrent players.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='EHL8 local QA bot runner (2 simultaneous participants max)')
    parser.add_argument('--host', default='127.0.0.1', choices=['127.0.0.1'])
    parser.add_argument('--port', default=45680, type=int)
    parser.add_argument('--rounds', default=25, type=int)
    parser.add_argument('--timeout', default=4.0, type=float)
    parser.add_argument('--pin-stdin', action='store_true', required=True,
                        help='PIN comes from stdin, never process arguments')
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args(argv)
    pin = sys.stdin.readline(16).strip()
    if len(pin) != 6 or not pin.isascii() or not pin.isdecimal():
        parser.error('PIN must be 6 ASCII digits on stdin')
    if not 1 <= args.port <= 65534 or not 1 <= args.rounds <= 25 or not 0.2 <= args.timeout <= 30:
        parser.error('Invalid port, round count or timeout')
    # The GUI launches the dedicated server immediately before this process.
    # Wait briefly for its local listener instead of failing the first round.
    deadline = time.monotonic() + 5.0
    while True:
        try:
            with __import__('socket').create_connection((args.host, args.port), timeout=0.3):
                break
        except OSError:
            if time.monotonic() >= deadline:
                break
            time.sleep(0.1)
    output = run_suite(args.host, args.port, pin, args.rounds, args.timeout,
                       progress=lambda line: print(line, flush=True))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.report.with_suffix('.partial')
    try:
        tmp.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
        tmp.replace(args.report)
    finally:
        tmp.unlink(missing_ok=True)
    print(f"Final: {output['rounds_passed']}/{args.rounds} rodadas OK. Relatório: {args.report}", flush=True)
    return 0 if not output['rounds_failed'] else 1


if __name__ == '__main__':
    sys.exit(main())
