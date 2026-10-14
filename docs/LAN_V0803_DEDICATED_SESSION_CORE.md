# Emerald Hybrid Multiplayer — EHL8 Dedicated SessionServer v0.8.3 M2/1–M2/3 Preview

**Experimental two-player overworld-preview.** O adaptador de cliente EHL8 agora existe no próprio Emerald e compila, usando o renderizador remoto anterior. O servidor dedicado e o launcher estão integrados, **mas a jogabilidade com dois Emeralds reais ainda não foi validada pelo usuário**. Não confundir este modo com batalhas/trocas via Cable Club: ainda são P2P e usam bytes TCP diferentes.

## Scope and rationale

The user confirmed v0.8.2 Windows installer works and authorized a MEGA update. Decisions 1–116 are authoritative; especially: 1B (playable host + dedicated), 3B/35A (four players final target), 73B (6-digit PIN), 77A (prevent same profile identity twice), 79A (safe manual-save backup), 81A (LAN without mandatory accounts), 87B (idle shutdown default 15min), 100A/116A (start with two fully tested participants; later scale to 3/4), 112A (dedicated admin inside launcher eventually), 115A (Windows first).

**Why separate protocol?** EHL8 is a versioned framed session transport. Legacy Cable Club TCP 45680 and Presence 45681 use different byte layouts. Mixing them would misinterpret handshakes, corrupt link state or cause stalls. This code does not alter any legacy code path.

## Implemented in this PR (M2 server, native game client and launcher beta)

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

1. **M2/2 — Cliente nativo implementado:** `src/lnet/lnet_session_client.c` e `src/link.c` já integram EHL8 ao renderizador. **PENDENTE** a confirmação visual com dois Emeralds reais e salvamentos preservados; modo P2P antigo segue separado.
2. **M2/3 — Launcher parcialmente implementado:** GUI já inicia/para processo dedicado, captura PIN sem expor argv e conecta um cliente EHL8. **PENDENTE:** lista dinâmica de participantes, ready/start visual, kick/admin e QR; não chamar de lobby completo.
3. **M2/4 — Reconnect:** #60A/#86A need 60-second reserved slots and authenticated session-bound reconnect tokens; absent in this milestone.
4. **M3 — Four players:** change session + viewport adapter to 3 remotes; only after 2-client real gameplay and regression QA.
5. **Security:** PIN is basic LAN authorization only; no encryption or trust-bound account authentication. Rate limit improvement and testing against resource exhaustion required prior to broader distribution.
6. **Android:** service foreground UI and Android host require dedicated native integration; packaged Windows PyInstaller executable cannot run on Android.
7. **Save guarantees:** server **never** touches saves. Existing save profile manager is structural-only; no post-save auto-backup/checksums yet. This is a separate blocking security task.

## Changes / verification / rollback

- **Added:** `tools/emerald_session_server.py`, `tests/test_emerald_session_server.py`, `.github/workflows/test-v0803-dedicated-server.yml`, this document; `AI_README.md` and `AGENTS.md` updated.
- **Modified game files:** `src/link.c`, `src/platform/sdl2.c`, `include/link.h`; novos `src/lnet/lnet_session_client.{c,h}`. Reutilizam sprites/remoto, não alteram mapas, eventos, save, batalha, audio, SIO, Quest UI, assets ou gameplay Hybrid original.
- **Removed:** NONE.
- **Rollback:** branch `feature/lan-v080-mega-desktop-polish` at SHA `3f94a665bc742d2130a856b5b153596def8445a4`; ultimate user-proven LAN v0.7.2.1 branch `feature/lan-v0721-viewport-culling` at SHA `a87e2c49e453db32def5e71ba2a2e696a911d504`.
- **Review status:** experimental draft; builds Windows/Android e testes C↔Python EHL8 aprovados, instalador/ZIP Preview validado no CI. **Somente a execução no Windows com dois personagens em Hoenn + saves ainda exige QA do usuário.** Consultar AI_README.md seção 21 para runs e hashes.


## M2/2–M2/3 — Cliente nativo + launcher Windows (2026-10-14)

**Código acrescentado (agora presente na branch deste documento):**
- `src/lnet/lnet_session_client.c/.h`: cliente de rede EHL8 C99 com TCP não bloqueante via `lnet_net_connect_nb`/`send_nb`/`recv_nb`, decoder incremental `lnet_session_v1`, estado HELLO→WELCOME→AUTH_PIN→JOIN→READY→START→POSE, heartbeats, timeout, perda de sprite quando pose expira, validação de sequência. **Não faz SIO, não recebe Pokémon/trades, não toca saves.**
- `src/link.c`: `PortLanRequestDedicatedClient()` ativa EHL8 opcional, mantém `sLanPresence` P2P antigo separado; reaproveita `PortLanPresencePump` com **o mesmo virtual sprite, interpolação e viewport culling aprovado pelo usuário**. Log de mudanças de estado sem PIN.
- `include/link.h`: declaração explícita da entrada EHL8, separada do host/client de Cable Club.
- `src/platform/sdl2.c`: novas flags `--session-client=IPv4:porta --session-pin-stdin`, mais `--session-pin=123456` apenas como alternativa manual de desenvolvimento. O perfil `--profile-root`/`--profile-id` é obrigatório, assim como porta 1–65534; rejeita tentar EHL8 junto com `--lan-host`/`--lan-client`. O launcher usa stdin para o PIN, evitando segredo no argv e logs. Nunca cai silenciosamente no save padrão.
- `tools/emerald_session_server.py`: `--pin-stdin` aceita PIN via pipe no início, sem expor senha na lista de argumentos; inicia headless e mantém protocolo e restrição a 2 slots.
- `tools/emerald_launcher.py`: adiciona controles para iniciar/parar processo `EmeraldSessionServer.exe`, PIN mascarado, opção **Entrar via servidor dedicado** para Jogar com Amigos, conexão EHL8 por IP; P2P antigo permanece padrão. Só permite uma sessão de jogo por vez por launcher. Logs de servidor/jogo em pasta de logs. Exibe estado ligado/desligado **não** lista real de jogadores em UI nesta etapa.
- `tests/native_ehl8_client.c`, `tests/test_ehl8_native_bridge.py`, `tests/test_emerald_launcher.py`: integração TCP real com dois binários nativos C + servidor Python, verificação de handshake/autenticação/ready/start/pose, rejeição de PIN inválido no launcher e ausência de PIN em argumentos.
- `scripts/verify_v080_profile_patch.py`: inversão estrita somente de novos trechos de flags SDL antes de auditar os hashes legados. Não enfraquecer comparações de áudio/turbo/saves.
- Workflows de Windows x86 e Android ARMv7 compilam a branch inteira; workflow EHL8 compila cliente em Linux e simula duas instâncias na rede local. A compilação não é QA jogável.

### Experiência real pretendida no preview

1. Em um PC servidor (pode também ser um PC de um dos jogadores), abrir `EmeraldLauncher.exe` e informar porta 45680 e PIN de 6 dígitos. Clicar **Iniciar servidor dedicado**; processo `EmeraldSessionServer.exe` fica independente de jogo.
2. No primeiro PC jogador, abrir launcher, selecionar seu perfil (novo ou importado de **cópia** do save), informar IP privado do servidor (ou deixar vazio **somente se o servidor estiver ativo no mesmo launcher**) e PIN. Marcar **Entrar via servidor dedicado EHL8** e escolher **Jogar com amigos**. O jogo abre com flags de perfil e PIN enviado via stdin.
3. No segundo PC jogador, fazer o mesmo com seu **próprio** perfil e IP do servidor; servidor só inicia o EHL8 GAME quando ambos estão READY. Cada personagem continua com sua própria história/save; sprite do amigo aparece somente quando estão no mesmo mapa e dentro da câmera.
4. Desconectou: cliente EHL8 marca falha e oculta sprite; **reconexão 60s reservada ainda não existe**. Fechar e reabrir a partida é alternativa experimental; primeiro backup.
5. Para troca/batalha usar, por enquanto, o **P2P Cable Club antigo** fora da sessão EHL8; **não é possível iniciar troca usando o servidor dedicado nesta versão**.

### Proibições e limites de aceitação

- **Não chamar de primeira v0.8 totalmente jogável/finalizada sem QA de duas instâncias reais do jogo.** O loopback C/C server passou no laboratório, mas a renderização do sprite no jogo, menu e save real ainda requerem captura manual em Windows/Android.
- Não dizer que o PIN é criptografado, que o servidor é seguro para WAN pública, nem abrir port forwarding: EHL8 tem PIN simples e transporte claro. VPN privada ou LAN confiável.
- M2/3 lobby gráfico **parcial**: há botões e estados de processo, mas ainda não há lista dinâmica de membros/admin, prévia de save no lobby, ações Kick, QR/discovery, reconexão.
- O servidor dedicado EHL8 **ainda não retransmite Cable Club SIO**. Os dois jogos podem andar e se ver; PvP e trocas seguem P2P antigo.
- O arquivo `.sav` é exclusivamente do jogo local. Sem auto-backup pós-save nem validador de checksums completo; copiar `.sav` antes de cada teste.
- **Sem qualquer asset novo, modificação de Hoenn, Quest UI, personagens base, spritesheet ou regras de batalha**; os resultados devem ser idênticos à versão anterior fora da presença dedicada.

### Compilações e handoff

Consultar workflows para o **SHA exato da última revisão**:
- `test-v0803-dedicated-server.yml`: Linux+Windows e prova C→Python→C de duas poses EHL8.
- `build-lan-hybrid-windows.yml`: executável Emerald x86 e regressão da build antiga.
- `build-lan-hybrid-android.yml`: compilação APK antigo (nova UI Android continua pendente).
- `build-v080-graphical-launcher.yml`: empacotamento GUI Windows.
- `test-lan-v080-foundation.yml`: perfil seguro em fixtures sintéticas e decoder.

O instalador v0.8.2 confirmado funcionando pelo usuário permanece na branch **`feature/lan-v080-mega-desktop-polish`**. Para rollback LAN/P2P, usar `feature/lan-v0721-viewport-culling` commit `a87e2c49e453db32def5e71ba2a2e696a911d504`. **Não substituir instalação anterior sem backup**.
