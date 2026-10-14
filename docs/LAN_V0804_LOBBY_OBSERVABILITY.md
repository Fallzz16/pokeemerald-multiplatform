# Emerald Hybrid v0.8.4 — Lobby observability (Windows, experimental)

## Purpose and non-claims

This increment fixes a misleading status in the graphical launcher: previously any **live process** was shown as an "active" EHL8 server even when the TCP listener had not bound or no players had joined.

Now the dedicated server publishes an **atomic local JSON snapshot**, and the launcher displays **actual joined profiles, ready states and lobby/playing status**. The data is a *local status channel* only, not a networked admin protocol. It must not be confused with proof of in-game visual QA or with the planned full lobby (#8B, #112A).

## Approved context

All 116 decisions remain in force. In particular: four players is the final goal, but **two tested first** (#100A/#116A); local saves and no mandatory online account (#81A); no public TCP ports; PIN for LAN only (#73B). The M2 preview game and v0.8.2 installer previously tested by the user are preserved.

## Changed files and behavior

- `tools/emerald_session_server.py`: optional `--status-file=<path>`. Emits schema v1 `{schema,state,port,capacity,players,updated_at}` on listener readiness, JOIN, READY, START, LEAVE and clean stop. Each `players` entry is `{slot,profile,ready}`. File is written through exclusive temporary file with `flush/fsync` and `os.replace`. It has no PIN, IP, Trainer ID, badges, Pokémon party, map, coordinates, or save data.
- `tools/emerald_launcher.py`: passes a local per-user `ehl8-lobby-status.json` in the `logs` directory. Deletes the *previous* snapshot **before launching**. `watch_server()` now displays actual `X/2` and identities/readiness, or "iniciando/status indisponível" when unavailable; detects process exit separately.
- Defensive reader: file length limit 8192, schema/port/status/slot/profile validation; corrupt/missing/stale port snapshots are ignored. Display text is informational and not trusted as a security token.
- `tests/test_emerald_session_server.py`: socket-level status lifecycle test for 2 connected, ready/start, disconnect and stop; checks that PIN isn't included.
- `tests/test_emerald_launcher.py`: verifies the GUI reader, valid names, bad port, malformed JSON and overlong data.
- `.github/workflows/test-v0803-dedicated-server.yml` and `.github/workflows/build-v080-graphical-launcher.yml`: added experimental branch to test triggers.

**Unchanged:** `pokeemerald.exe`, `src/`, GBA assets, save manager, Cable Club P2P, PokéNav, map logic, Android/game source, previous run/artifact binaries. **Removed:** no feature.

## QA and distribution gate

1. Run dedicated session suite **on Linux and Windows**, plus the compiled C↔Python bridge and Windows PyInstaller server.
2. Run launcher Python unittest and Windows PyInstaller launcher. A CI success does **not** prove two actual game processes rendered each other's avatars.
3. For a user-facing build, bundle the **new** `EmeraldLauncher.exe` and `EmeraldSessionServer.exe` from their respective successful runs with the already tested compatible game/SDL2/profile-tool binaries, pinning each SHA256 and refusing missing components or any .sav.
4. Test *on user hardware*: 2 isolated profiles, host process without game, two Emerald windows, progress/save/reopen, camera/warp, disconnect. Confirm occupancy and status transitions on launcher.
5. Do not claim the full admin lobby until dynamic controls, invitations, late join/resume (#60A 60s), timeout/kick, Android UX and 3/4 player scaling are implemented and validated.
6. Do not open EHL8 directly to public internet. LAN PIN is **not encryption**. No online account or cloud data available here.

## Rollback and next iteration

Rollback first to prior experimental `feature/lan-v0803-dedicated-session-core` [PR #10](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/10), then to the user-approved v0.8.2 install in `feature/lan-v080-mega-desktop-polish`, or to LAN P2P v0.7.2.1 for the established baseline. **No saves are touched** by this increment.

Next: real-world gameplay QA, UI admission list/Ready controls, 60-second reserved slots with authenticated reconnection, and integration of 2 players before moving to 3/4. The dedicated server still **does not relay SIO battles/trades**.

## Tool and testing status

See `AI_README.md` and PR for exact GitHub Actions run IDs and conclusions. Do not report tests as passing without inspecting the relevant run.
