# Emerald Hybrid — remote private VPN readiness QA (candidate v0.7.2.2)

## Scope

**Two players only**, over either a shared physical LAN or a trustworthy routed IPv4 VPN such as Tailscale. This is a usability/QA increment based exactly on `feature/lan-v0721-viewport-culling`, SHA `a87e2c49e453db32def5e71ba2a2e696a911d504`. **No game code changed** here. External LAN gameplay was tested by the user previously; WAN-through-VPN gameplay was **not** tested.

## Acceptance checklist — must happen on two different ISP networks

| Step | Expected | Status |
|---|---|---|
| 1. Win10/11 host and client with separate saves | Each trainer has own .sav; backups saved outside candidate folder | PENDING real two-device |
| 2. Tailscale accessible to each user | IPv4 endpoint visible, host machine shared with client, access policy permits game | PENDING |
| 3. Host launcher starts port 45680 | Game starts, `host-vpn.log` indicates listening | PENDING |
| 4. Client diagnostic on TCP 45680 and 45681 | Both accessible while host game is running | PENDING |
| 5. Join using host's actual IPv4 and correct port | Two game clients connect; check errors/retries | PENDING |
| 6. Same town/route, move both directions | Remote sprites show in camera only; no duplicates, stutters or stale sprites | PENDING |
| 7. Leave camera; route changes; re-enter | Peers remain synced; hide/show correct; no unnecessary FPS loss | PENDING |
| 8. In-game Cable Club trade and duel | State progresses, no hang, both maintain exact Pokemon/progress across save+reopen | PENDING, high-risk under jitter |
| 9. Controlled VPN interruption and reconnect | No corruption, suitable timeout, recover manually if needed | PENDING |
| 10. Test direct path and VPN DERP relay if possible | Record RTT, packet jitter symptoms; avoid claiming a relay-backed link is universally stable | PENDING |
| 11. Re-test offline startup and original LAN | Feature adds no new persistent state and does not alter previous gameplay | PENDING UI; baseline user-approved |

## Automated QA

- PowerShell parser and dry-run entrypoint tests via `.github/workflows/test-remote-vpn-launcher.yml`, Windows runner.
- Static review: `src/lnet/lnet_net.c` binds `INADDR_ANY` for IPv4; client uses `inet_pton(AF_INET)`. `src/link.c` opens presence on `base+1`.
- Native `scripts/verify_lan_foundation.sh` tests prior link/serial/presence/culling. No changes made to those tests or native protocol.
- Successful standalone launcher tests do **not** prove Internet gameplay, Tailscale access controls, real movement, saving, latency or trading.

## Debugging without exposing the machine publicly

1. Confirm both are logged in to Tailscale and can reach the **host's Tailscale IPv4** (not public home IP).
2. Start host BEFORE client `-Mode Check`; verify both TCP channels.
3. Check whether the firewall rule for each port restricts source IPv4 to the friend's private Tailscale device IP. If blocked, adjust the minimum required scoped rule manually; launcher never creates firewall rules. Windows may classify VPN as Public, so a Private-only rule may not apply.
4. Run two separate game folders/saves. Record `host-vpn.log` and `cliente-vpn.log`, scrub any private IP/user paths before sending.
5. If presence works but Cable Club fails under higher RTT, roll back to baseline LAN use; do not alter speed/turbo/handshake timings without dedicated QA.
6. NEVER forward TCP 45680/45681 on public router; legacy link protocol has **no encryption or authentication**.

## Shipping gate and release terminology

- Product phase **two-player LAN**: previously tested by user on v0.7.2.1.
- Candidate **VPN remote private access**: script and documentation QA automated, but **not final** until 2-network test above.
- **Native WAN multiplayer / dedicated server / 4 players / launcher GUI v0.8**: NOT implemented.
- Merge into a stable release only after recorded two-network gameplay and safe trade/save verification. Keep PR draft meanwhile.

## Rollback and source integrity

Base remains `feature/lan-v0721-viewport-culling` SHA `a87e2c49e453db32def5e71ba2a2e696a911d504`; gameplay C sources, Android and GBA data are identical. Remove scripts to recover baseline without save migrations. No save data is included in this feature branch. Contact next AI with `AI_README_REMOTE_VPN.md` and `README_VPN_PTBR.md`.
