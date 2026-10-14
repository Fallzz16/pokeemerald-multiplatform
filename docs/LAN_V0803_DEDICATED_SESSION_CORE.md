# Emerald Hybrid Multiplayer — EHL8 Dedicated SessionServer v0.8.3 M2/1

**Experimental networking component. NOT PLAYABLE AS A DEDICATED GAME SESSION YET.** This service receives EHL8 clients, not the existing raw SIO/Presence sockets used by `pokeemerald.exe` from v0.7.2.1. **Do not enable the dedicated-server UI mode for ordinary players until a compatible game-side SessionClient exists and has passed QA.**

## Scope and rationale

The user confirmed v0.8.2 Windows installer works and authorized a MEGA update. Decisions 1–116 are authoritative; especially: 1B (playable host + dedicated), 3B/35A (four players final target), 73B (6-digit PIN), 77A (prevent same profile identity twice), 79A (safe manual-save backup), 81A (LAN without mandatory accounts), 87B (idle shutdown default 15min), 100A/116A (start with two fully tested participants; later scale to 3/4), 112A (dedicated admin inside launcher eventually), 115A (Windows first).

**Why separate protocol?** EHL8 is a versioned framed session transport. Legacy Cable Club TCP 45680 and Presence 45681 use different byte layouts. Mixing them would misinterpret handshakes, corrupt link state or cause stalls. This code does not alter any legacy code path.

## Implemented in this PR (first M2 server milestone)

- `tools/emerald_session_server.py`: dedicated network service using Python stdlib `asyncio`; no SDL/game rendering, no AgbMain, no `.sav` access.
- Accept up to **two authenticated profiles** concurrently, plus bounded connections pending handshake.
- 28-byte big-endian EHL8 header matching `src/lnet/lnet_session_v1.c`. Reject magic, version, flags, length >4096, invalid types and fragmented bad headers.
- HELLO => WELCOME with session ID/slot capacity; AUTH_PIN for six ASCII digits; JOIN with local profile ID pattern `[A-Za-z0-9_-]{1,48}`. Reject duplicate IDs and full lobby.
- Ready flag, peer list and START when both are ready; HEARTBEAT; LEAVE, last-player cleanup.
- After START: accepts valid 18-byte **LANP v1** poses from clients and forwards to other connected EHL8 peer with a 1-byte sender slot prefix. Reject coordinates outside 0–2047, invalid direction/appearance, stale sequence and spam. Relay message payload is 19 bytes.
- Use nonblocking asyncio I/O, 35-second read timeout, limited output buffer size and bounded `drain()`, no data persisted from other players. A startup administrator PIN is validated but **is not sufficient to run a service exposed to public internet**.
- Progressive cooldown for repeated wrong PINs from same remote IPv4, no PIN or save data printed to logs.
- Idle shutdown after 15 minutes when no clients are connected (configurable).
- Executable Windows `EmeraldSessionServer.exe` from the CI workflow with PyInstaller, **for protocol and lobby diagnostics only**. The game still uses old LAN P2P until SessionClient integration is implemented.

### Envelope

```text
magic[4]          "EHL8"
major:u16         1
minor:u16         0
message_type:u16  IDs below
flags:u16         0
payload_size:u32  0..4096
session_id:u64    0 for HELLO, otherwise WELCOME.session_id
request_id:u32    caller correlation
payload[0..4096]
```

Message type enum matches `src/lnet/lnet_session_v1.h`:
`HELLO=1 WELCOME=2 INCOMPATIBLE=3 AUTH_PIN=4 JOIN=5 PLAYER_LIST=6 READY=7 START=8 LEAVE=9 KICK=10 HEARTBEAT=11 POSE=12`.

**M2 payload contracts (new, must not change silently):**
- HELLO: empty; WELCOME: one byte slots; session ID in header.
- AUTH_PIN client: ASCII six-digit PIN; response: one byte `1`; failure sends KICK reason and closes.
- JOIN client: ASCII profile identifier 1..48; response one byte assigned slot 1/2.
- PLAYER_LIST broadcast: count `u8`; for each peer: slot `u8`, ready `u8`, name_length `u8`, profile_id bytes. Profile IDs are not proof of ownership; do not send a trainer's full save/Trainer ID as a token.
- READY: one byte 0 or 1; START: empty; HEARTBEAT: empty.
- POSE client: 18-byte legacy LANP v1 packet. POSE relay: `sender_slot:u8 + LANP[18]`. Bad packets close the offending connection. Position data is advisory; server is not anti-cheat authoritative.
- LEAVE broadcast: one-byte leaving slot.
- PIN not included in QR by default. Server has **no full user authentication**, no encryption, no WAN safety, and not yet a reconnect-resume token.

## Testing and commands

Test from repo root:

```shell
python -m unittest discover -s tests -p test_emerald_session_server.py -v
python -m py_compile tools/emerald_session_server.py
python tools/emerald_session_server.py --bind 127.0.0.1 --pin 123456 --port 45680
```

The default binds to `127.0.0.1` **only for local development**. To accept devices on your *trusted private LAN*, use `--bind 0.0.0.0`; do not port-forward to the public Internet. Keep firewall access scoped to your private LAN/VPN.

`--slots 1|2`, `--idle-minutes 1..1440`, `--port 1..65534`. Use a different PIN for every room.

The CI workflow `.github/workflows/test-v0803-dedicated-server.yml` runs **real socket integration tests** on Ubuntu and Windows and builds a standalone Windows executable. Test includes two joins, readiness, pose relay, duplicate/third user rejection, invalid PIN cooldown, malformed/oversized/incompatible frames, and preservation of service after bad connections.

Do not interpret passing CI as in-game integration. No launcher button activated; no APK prepared; no public release.

## Known limitations / required next milestones

1. **M2/2 — Client adapter:** integrate `EHL8` SessionClient with existing game's presence renderer for 2 remote clients, with load/save local profile as already designed; keep legacy P2P mode as fallback.
2. **M2/3 — Lobby integration:** launcher connects to server, shows PIN, player count, ready/start and error details. Dedicated server start/stop and logs from GUI. Cannot claim this before it works.
3. **M2/4 — Reconnect:** #60A/#86A need 60-second reserved slots and authenticated session-bound reconnect tokens; absent in this milestone.
4. **M3 — Four players:** change session + viewport adapter to 3 remotes; only after 2-client real gameplay and regression QA.
5. **Security:** PIN is basic LAN authorization only; no encryption or trust-bound account authentication. Rate limit improvement and testing against resource exhaustion required prior to broader distribution.
6. **Android:** service foreground UI and Android host require dedicated native integration; packaged Windows PyInstaller executable cannot run on Android.
7. **Save guarantees:** server **never** touches saves. Existing save profile manager is structural-only; no post-save auto-backup/checksums yet. This is a separate blocking security task.

## Changes / verification / rollback

- **Added:** `tools/emerald_session_server.py`, `tests/test_emerald_session_server.py`, `.github/workflows/test-v0803-dedicated-server.yml`, this document; `AI_README.md` and `AGENTS.md` updated.
- **Modified game files:** NONE. No alterations to `src/`, maps, characters, save logic, assets, SIO, UI, or Quest system.
- **Removed:** NONE.
- **Rollback:** branch `feature/lan-v080-mega-desktop-polish` at SHA `3f94a665bc742d2130a856b5b153596def8445a4`; ultimate user-proven LAN v0.7.2.1 branch `feature/lan-v0721-viewport-culling` at SHA `a87e2c49e453db32def5e71ba2a2e696a911d504`.
- **Review status:** experimental draft; update this section with **real CI run IDs/conclusions** and any bugs discovered before claiming tested Windows binary.
