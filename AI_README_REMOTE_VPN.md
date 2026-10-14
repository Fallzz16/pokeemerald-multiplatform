# AI handoff — Emerald Hybrid v0.7.2.2 (Windows remote-access VPN candidate)

Read this document, `README_VPN_PTBR.md`, `LAN_V0722_REMOTE_VPN_QA.md` and the branch head before any further change.

## Scope, history and fact checks

- Original repo `Fallzz16/pokeemerald-multiplatform`.
- Tested by the user: LAN P2P two-player Cable Club + remote sprite/viewport culling on `feature/lan-v0721-viewport-culling` commit `a87e2c49e453db32def5e71ba2a2e696a911d504`.
- This branch `feature/lan-v0722-remote-vpn-readiness` is created **directly** from that known-good SHA. It intentionally does not contain unfinished v0.8 M0/M1 features. PR for this branch remains draft until remote-network runtime QA.
- Separately developed v0.8 M0/M1 resides in `feature/lan-v080-m0-m1-foundation`, PR #6. Future plan approved 100 decisions and `AI_README.md` in that branch. **Do not confuse** experimental v0.8 native save profile with the stable older `pokeemerald.sav` behavior here.
- Real remote through two ISPs not yet demonstrated; do not announce this as native Internet multiplayer or certified WAN support.

## Technical assumptions verified in source

- `src/platform/sdl2.c` parses `--lan-host=<port>` and `--lan-client=<numeric IPv4>:<port>`.
- `src/lnet/lnet_net.c` binds host TCP to `INADDR_ANY`; client calls `inet_pton(AF_INET)`, so it requires a literal IPv4, not Tailscale MagicDNS or IPv6.
- `src/link.c` opens second presence TCP channel on `port + 1`, so base port MUST be 1..65534, default 45680; presence 45681. Caller must permit both TCP ports on trusted VPN interface/firewall.
- No authentication/authorization/TLS built into this legacy LAN game. Do not advocate forwarding public router ports or using DMZ.

## Changes made in this branch

**Added:**
- `INICIAR_EMERALD_VPN.ps1`: standalone PowerShell menu with Offline / Host playable / Join by numeric IPv4 / Test two TCP ports; validates ports and IPv4; `-DryRun` to exercise CLI without starting game.
- `INICIAR_EMERALD_VPN.bat`: entrypoint with process-local execution policy bypass, never administrative elevation; launches only the local reviewed script.
- `README_VPN_PTBR.md`: manual for same-LAN or Tailscale remote two-PC private sessions, backup of each player's own save, firewall/security, troubleshooting.
- `LAN_V0722_REMOTE_VPN_QA.md`: two-ISP, Cable Club, movement, save verification, network-failure checks, debug and rollback.
- `.github/workflows/test-remote-vpn-launcher.yml`: Windows PowerShell parser/dry-run CI.
- This handoff file.

**Modified game files:** none. No changes to `src/`, `include/`, `data/`, assets, `.sav`, maps, battles, quests, audio, fast-forward, SDL2 or Android.

**Removed:** none.

## Test status, do not invent

- Static source review confirms LAN listen/connect and port+1; native LAN tests were previously passing and game worked on LAN for user.
- Launcher CI runs Windows PowerShell AST syntax and command dry-run tests (valid/invalid IP/port; correct two ports), once published. Consult exact workflow SHA/runs before saying 'passed'.
- **Not tested in this branch:** 2 different internet connections, real Tailscale relay, multiplayer gameplay, trades, battles, saves, Android VPN.
- **No Tailscale installation is embedded or performed automatically.** Users install from its official source with independent accounts or explicit sharing/access grants.

## Mandatory verification before closing PR

1. Confirm diff from `feature/lan-v0721-viewport-culling`: **only docs/scripts/workflow**.
2. Confirm Windows launcher syntax/positive/negative cases pass in GitHub Actions.
3. Optional: bundle only **verified** v0.7.2.1 PE32 `pokeemerald.exe`/SDL2.dll with scripts into test candidate ZIP; never include any .sav or fabricate download paths.
4. Ask user for real PC-A host / PC-B client different networks QA logs from `LAN_V0722_REMOTE_VPN_QA.md`; test sprite, route transition, Cable Club, save/reopen and VPN disconnection.
5. Only merge/release when the real remote QA is sufficiently green. Otherwise label "experimental ready to test", do not call fully finished.

## Rollback / next steps

Delete added scripts and return to base branch commit `a87e2c49e453db32def5e71ba2a2e696a911d504` to recover the user-tested LAN code. Preserve backups and personal saves. The full modern launcher's offline/host/join menus, Android profile selection, dedicated server and four-player multiplayer belong to v0.8 work and must not be claimed for this remote VPN script.

Every further change must update this document with: branch, SHA, what added/modified/removed, tests (actual results), rollback, bugs/risks, what's NOT implemented, and next steps. Do not rebuild from zero after interruption.

## QA record — 2026-10-14

**Reviewed code commit:** `c4c833f5397bf76b6744caa1beece68dbb991b35`; **PR:** [#7](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/7), draft.

- **Windows PowerShell AST parser + 11 validation scenarios:** [Actions 38508291457](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38508291457), SUCCESS. Earlier 2 workflow attempts failed due to **harness only**: capturing expected negative-case STDERR and propagating the final test's expected child exit code 1. Both were corrected and the final run passed.
- **Windows x86 full game build + previous serial/transport regressions:** [Actions 38508291481](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38508291481), SUCCESS; workflow artifact ID **11869081465**, `Emerald-Hybrid-LAN-v0.7.2.2-RemoteVPN-Windows-x86-EXPERIMENTAL`. Includes Win32 `pokeemerald.exe`, `SDL2.dll`, launcher, wrapper and AI+PTBR README. ZIP verified in current assistant container via `zipfile.testzip()`, no .sav included, about 12.45 MB compressed. SHA256 of original artifact `e27c4cfd87234d4747adda1230083e8b1dffabf807e407848a32ba5844d19cd8`.
- **Generic legacy ROM compare CI:** [Actions 38508291511](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38508291511), FAILURE during `Compare`. Record it, do not imply all workflows green. Windows P2P build is a separate successful job.
- **Diff from user's prior-working LAN commit:** only remote VPN scripts, test runner, CI packaging workflow and Markdown; no changes under `src/`, `include/`, `data/`, saves or game logic.
- **CRITICAL STILL OPEN:** The two-ISP/two-PC Tailscale gameplay acceptance checklist has NOT been executed by user. Neither trade nor battle/save reliability over actual Internet RTT is verified. Do not claim "full multiplayer Internet finished". This is a **ready-to-test candidate**, not a stable WAN release.

**Update / removal summary:** added remote menu and dry-run tests, detailed manual and handoff; changed packaging workflow; removed nothing. **Not implemented:** native account/auth, dedicated server, four players, cross-network Android UI, automatic VPN install, public Internet multiplayer.
**Rollback:** v0.7.2.1 `feature/lan-v0721-viewport-culling` SHA `a87e2c49e453db32def5e71ba2a2e696a911d504`.
**Next step:** have user test with two PCs in separate networks and different original saves; capture logs/latency, transitions, battle/trade, save/restore, and only then consider PR graduation from draft. Maintain this handoff on every subsequent update.
