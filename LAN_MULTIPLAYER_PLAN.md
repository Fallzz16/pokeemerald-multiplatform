# Emerald Hybrid v0.7.0 — LAN compatibility branch (experimental)

**Implementation branch:** `feature/lan-hybrid-v070` from `emerald-hybrid-v0.7.0` at `322409d4a5516a27e04ea3b9afa70229c90bab05`.

This branch is deliberately **not** merged into the released Hybrid source. All current Fairy/PSS, QoL, fast-forward, Quest UI, Sprite Bridge, maps, encounters and save layouts are retained. This is an incremental LAN integration with a native transport; it has not yet passed a two-device battle/trade gameplay test.

## Added
- A native TCP host/client LAN link transport (`src/lnet/`) adapted from [kuangyl0212/pokeemerald-multiplatform](https://github.com/kuangyl0212/pokeemerald-multiplatform) `v0.4.1-lan-multiplayer`, with its fork-scoped MIT port-modification license. The socket implementation includes a bounded send/receive timeout and a protocol revision marker; both peers must use this build.
- The existing Emerald serial SIO transfer path for normal wired link operations, activated only with `PORTABLE`. The GBA ROM path remains conditional.
- Native Windows command-line connection options; Android `INTERNET` permission and a minimal platform launcher (offline/host/client). The Android launcher supplies arguments to SDL; no save migration.
- Isolated Linux TCP transport unit tests in `tests/`, runnable with `bash scripts/verify_lan_foundation.sh`.
- A CI candidate build workflow with Windows artifact for testing, **not** a stable release.

## PC setup (experimental)
1. Run the same Hybrid LAN candidate build on both PCs. Back up `pokeemerald.sav` first.
2. Start host: `pokeemerald.exe --lan-host=45680`.
3. On another PC in the same Wi-Fi / local network, start `pokeemerald.exe --lan-client=192.168.1.50:45680`. Replace the example IP with the host's local IPv4 address (find using `ipconfig`).
4. On both clients use the original Emerald Cable Club link NPC to attempt battles/trades. The LAN socket alone does not automatically open a battle or trade UI. Allow inbound TCP port 45680 in the host firewall if prompted.
5. To gather logs use `--lan-log path/to/file.log` **before** the networking flag (e.g. `pokeemerald.exe --lan-log host.log --lan-host=45680`).
6. Without flags, the original offline mode should behave as before.

## Android setup (experimental, APK **not yet verified**)
Android SDK/NDK/SDL2 sources and a compatible Android build environment are required to build the app. The Android launcher offers **Play offline**, **Host LAN**, and **Join LAN** with a host IPv4 and TCP port (default 45680). Both peers must join the same local network. No internet relay server is provided. The target is still 32-bit ARMv7; 64-bit-only Android devices are not supported in this phase.

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
