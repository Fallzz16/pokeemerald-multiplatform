# Emerald Hybrid v0.7.0 — LAN compatibility branch (experimental)

**Implementation branch:** `feature/lan-hybrid-v070` from `emerald-hybrid-v0.7.0` at `322409d4a5516a27e04ea3b9afa70229c90bab05`.

This branch is deliberately **not** merged into the released Hybrid source. All current Fairy/PSS, QoL, fast-forward, Quest UI, Sprite Bridge, maps, encounters and save layouts are retained. This is an incremental LAN integration with a native transport; it has not yet passed a two-device battle/trade gameplay test.

## Added
- A native TCP host/client LAN link transport (`src/lnet/`) adapted from [kuangyl0212/pokeemerald-multiplatform](https://github.com/kuangyl0212/pokeemerald-multiplatform) `v0.4.1-lan-multiplayer`, with its fork-scoped MIT port-modification license. The socket implementation includes a bounded send/receive timeout and a protocol revision marker; both peers must use this build.
- The existing Emerald serial SIO transfer path for normal wired link operations, activated only with `PORTABLE`. The GBA ROM path remains conditional.
- Native Windows command-line connection options; Android `INTERNET` permission and a minimal platform launcher (offline/host/client). The Android launcher supplies arguments to SDL; no save migration.
- Isolated Linux TCP transport unit tests in `tests/`, runnable with `bash scripts/verify_lan_foundation.sh`.
- CI candidate builds for **Windows x86** and **Android ARMv7**. Both compile and produce downloadable artifacts; neither is a stable release.

## PC setup (experimental)
1. Run the same Hybrid LAN candidate build on both PCs. Back up `pokeemerald.sav` first.
2. Start host: `pokeemerald.exe --lan-host=45680`.
3. On another PC in the same Wi-Fi / local network, start `pokeemerald.exe --lan-client=192.168.1.50:45680`. Replace the example IP with the host's local IPv4 address (find using `ipconfig`).
4. On both clients use the original Emerald Cable Club link NPC to attempt battles/trades. The LAN socket alone does not automatically open a battle or trade UI. Allow inbound TCP port 45680 in the host firewall if prompted.
5. To gather logs use `--lan-log path/to/file.log` **before** the networking flag (e.g. `pokeemerald.exe --lan-log host.log --lan-host=45680`).
6. Without flags, the original offline mode should behave as before.

## Android setup — compiled APK, device gameplay not yet verified

The Android ARMv7 **debug APK has passed Gradle/CMake compilation and the static packaging smoke test** (debug signature, package ID, app launcher, `INTERNET` permission, Android API level and SDL2/native game libraries). This does **not** prove it will open and play successfully on a specific phone, nor that battles and trades work between two players.

1. Open [Android Actions run 38481403085](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38481403085), find **Artifacts**, download `Emerald-Hybrid-LAN-v0.7.0-Android-armv7-Experimental`, extract `app-debug.apk` and install it on a compatible Android device.
2. Use **Play offline** first. Verify the game starts, controls respond, save/reload works, and the Quest UI/Fairy/PSS features remain correct.
3. Use **Host LAN** on one device: its local IPv4 is displayed before starting the game; port defaults to `45680`.
4. Use **Join LAN** on the other device, entering `HOST_IP:45680` (or just `HOST_IP`). Both must be on the same local Wi-Fi/accessible LAN. Avoid guest Wi-Fi with client isolation.
5. Enter the in-game Cable Club on both players and attempt a linked battle and trade. Both devices must run this same experimental build.
6. For a cross-platform test, run `LAN_HOST.bat` or `LAN_JOIN.bat` from the matching [Windows Actions run 38481402987](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38481402987), and use the same IPv4/port.

**Limitations:** This APK packages **32-bit ARMv7 only**; some 64-bit-only Android phones cannot install it. It does not include an Internet matchmaking/relay service or shared overworld. Only the original link-cable flow is the current test target.

**Save/signature warning:** GitHub Actions debug APKs may be signed with different temporary signing keys on different runs. If Android reports an incompatible-signature update, **do not uninstall first without backing up your existing in-app save**. These are independent experimental builds, not a guaranteed seamless upgrade path. Keep backup copies of every Windows `pokeemerald.sav` as well.

## QA observations / current evidence (2026-10-13)

- ✅ Windows x86 build, Hybrid v0.7.0 regression suite, and 71 native LAN transport checks completed successfully.
- ✅ Android ARMv7 Gradle/CMake build completed; package signature, contents, ABI and launcher validation passed.
- ☐ Android installation and real in-game startup on a physical device: not yet verified.
- ☐ Windows ↔ Windows, Android ↔ Android and Windows ↔ Android Cable Club battles and trades: not yet verified.
- ☐ Disconnect/reconnect, Wi-Fi interruptions, simultaneous save, latency, lifecycle, fast-forward and multi-hour gameplay: not yet verified.

## Required acceptance gates before stable
- Clean Windows native compilation and Android Gradle/CMake compilation; inspect CI logs.
- Launch and finish a real two-player linked battle on Windows/Windows, then Android/Android, then cross-device Windows/Android; test trade end-to-end in the same combinations.
- Test mismatched build rejection, disconnect mid-battle/trade, Wi-Fi interruption, menu cancellation and reconnection without permanent game freezes.
- Compare original game data, run v0.7 verifier and save/load with backup copies, including malformed and mixed-version link data.
- Confirm Android UI/touchscreen and background/foreground lifecycle, performance and audio under LAN load.

## Multiplayer mode C: next phase (not implemented)
After link battles/trades prove reliable, implement a separate map-player replication protocol (map/instance ID, position, direction, movement state, snapshots/interpolation, joins/leaves, validation). No world-shared player avatars or persistent world state is implemented in this branch. Do **not** claim MMO/co-op functionality yet.

## Licensing
The adapted LAN networking code is based on the upstream fork's MIT-scoped **original port modifications**. Its license and copyright notice apply to those parts; this does not license Pokémon names, sprites, music or the upstream decompilation. Avoid publishing copyrighted game data without the appropriate rights.


## Follow-up candidate: asynchronous serial-slot hardening (isolated branch)

Branch: `feature/lan-v070-async-slot-hardening`, derived from `feature/lan-hybrid-v070`. This branch has **not** been merged. It changes only the LAN transport/controller/tests/CI, not the baseline ROM's Fairy/PSS, Quest UI, maps, sprite pipeline, or save layout.

### Motivation

The original TCP HELLO/setup polls non-blockingly, but `lnet_session_exchange` used blocking `send_all` / `recv_all` on each serial word. That could hold the game's own native thread for up to the socket timeout when a peer paused, lost Wi-Fi, or closed. To avoid game-thread stalls, this candidate:

- Keeps a partially-sent or partially-received three-byte SLOT frame in the session across game frames, with return values `1=complete`, `0=pending`, `-1=failure`.
- Adds client-connect, HELLO, and active-slot deadlines. The host listener intentionally has no connection-wait deadline.
- Makes the serial callback run **only after** the pair of slot values is fully exchanged.
- Stops further callbacks after a failed exchange; preserves serial register behavior when offline.
- Applies conservative send-queue backpressure: the game callback pauses when four outgoing commands await serial delivery; SIO continues pumping, rather than discarding queued commands.
- Extends the native session/link tests with a deliberately delayed client and adds a mid-slot peer-disconnect regression check.
- Enables the existing Windows and Android Actions workflows on this test branch too.

### Required validation before merge

The earlier 71 passing checks and green Windows/Android artifacts apply to the previous `feature/lan-hybrid-v070` HEAD, **not automatically to this new candidate**. Re-run:

```bash
bash scripts/verify_lan_foundation.sh
EMERALD_LAN_QA=1 bash scripts/verify_v070.sh
```

Then inspect the candidate branch's Windows and Android workflow results, plus perform the physical-device and full Cable Club battle/trade acceptance matrix. In particular verify that asynchronous one-word RTT and queue backpressure do not reduce link throughput unacceptably, deadlock the Cable Club, overflow receive queues, or desynchronize transfers. Do not mark the candidate stable from static inspection alone.

**Known remaining risks:** the serial protocol still pays per-word TCP round-trip time; heavy Wi-Fi latency can make gameplay pause while the queue drains, and the Android app lifecycle, real game/save round-trips and cross-platform trade/battle have not been verified. A frame-batched protocol or dedicated, well-specified serial service may be needed after measuring two-player traces. Shared Hoenn overworld is still out of scope.
