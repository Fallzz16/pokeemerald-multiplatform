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


## Incremento de estabilidade: entrada tardia + ocupação real do lobby (2026-10-14)

**Problema detectado na revisão do código:** o servidor admite que um jogador entre quando a sessão já está no estado `GAME`, mas o cliente nativo EHL8 sempre envia `READY=1` depois de receber `JOIN`. Antes desta correção, o servidor aceitava READY somente em `LOBBY`, portanto a entrada tardia era rejeitada imediatamente após `START`. Isso contrariava as decisões #9A/#38A/#61A e interrompia a substituição de um jogador que saiu.

**Corrigido:**
- `tools/emerald_session_server.py`: em `GAME`, o primeiro `READY=1` válido da pessoa que acabou de entrar é aceito como confirmação. Mensagens READY repetidas são idempotentes e **não geram broadcasts extras**. Payload diferente de `1` continua inválido; outras mensagens não autorizadas continuam rejeitadas.
- `tests/test_emerald_session_server.py`: teste de socket real inicia uma sala com 2 jogadores, aguarda `START`, desconecta um, entra terceiro perfil substituto no slot liberado, confirma `START`, envia READY e HEARTBEAT e recebe o encaminhamento correto de uma pose. Também verifica que READY duplicado não injeta `PLAYER_LIST` extra.
- `tools/emerald_session_server.py` registra somente `EHL8_ROOM_COUNT=N/2` para início, entrada e saída, sem expor nome de treinador, IP ou PIN.
- `tools/emerald_launcher.py`: painel de servidor mostra ocupação **real e atualizada** no formato `jogadores conectados: N/2`, lendo somente os 8192 bytes finais do log da instância iniciada. Logs ausentes/malformados deixam o texto em estado de aguardo, sem inventar números.
- `tests/test_emerald_launcher.py`: testes de parser com várias linhas, logs ausentes, dados inválidos e final de arquivo longo.

**Não alterado:** `src/` e comunicação do Emerald, grafismo/culling, progresso, saves, Cable Club e binários já instalados. **Não removido:** nenhuma funcionalidade. As alterações são de servidor, painel administrativo, testes e documentação.

**Limites que permanecem:** este caso cobre *entrada tardia com slot livre*, mas **não implementa reconexão com reserva de 60 segundos ou autenticação de sessão retomada**. O novo contador é apenas uma informação resumida — ainda falta lobby gráfico completo com participantes/Pronto/kick, admin avançado e interação dentro do jogo. PIN continua adequado apenas a LAN/VPN privada. Builds CI e teste de sockets não substituem QA real de duas janelas Emerald no Windows.

**Validação:** conferir `.github/workflows/test-v0803-dedicated-server.yml` (Linux, Windows, ponte C nativa), `build-v080-graphical-launcher.yml`, builds completos Windows/Android e packaging EHL8 Preview **na revisão exata** do último commit. O CI genérico da ROM é independente e pode continuar falhando no alvo antigo. Não declarar a correção pronta para release se esses checks ou a QA humana falharem.

**Rollback e handoff:** a branch de trabalho continua `feature/lan-v0803-dedicated-session-core` / PR #10 draft. A instalação v0.8.2 anteriormente aprovada permanece inalterada; todos os testes devem usar a preview EHL8 em pasta/instalação separada com **cópias dos saves**. Registrar resultados finais com SHA e IDs de runs também em `AI_README.md`.


## M2/4 — Reserva de vaga e reconexão automática por 60 segundos (PR #13)

**Situação:** código experimental; validar no GitHub Actions e depois em dois jogos Windows reais. Decisões do usuário #60A/#86A. Este documento tem seções históricas; esta seção substitui a anotação anterior de que reconexão não existia.

### Contrato compatível com EHL8 1.0

O framing EHL8 de 28 bytes, tipos, porta e stream de poses LANP **não mudam**. O tipo `JOIN=5` ganha uma extensão opcional no **payload**:

| JOIN do cliente | Resposta JOIN do servidor | Resultado |
|---|---|---|
| `profile_id` ASCII puro (legado) | 1 byte `slot` | Modo antigo, sem reserva/reconexão |
| `profile_id + 0x00` | `slot:u8 + resume_secret[16]` | Credencial aleatória de retomada |
| `profile_id + 0x00 + resume_secret[16]` | `slot:u8 + new_resume_secret[16]` | Retomada autenticada, **mesmo slot**, credencial antiga descartada |

Regras de segurança:
- `resume_secret` contém **128 bits imprevisíveis** (`secrets.token_bytes(16)`) e é enviado exclusivamente por dentro da conexão TCP privada; nunca incluí-lo em `PLAYER_LIST`, arquivo .sav, README, QR ou logs. É **token de posse transitória**, não login online criptográfico; EHL8 ainda **não é cifrado**.
- O segredo precisa coincidir com a identidade e com a vaga reservada. `profile_id` sozinho **não** permite recuperar a vaga; outros perfis são impedidos de ocupar a vaga reservada enquanto a janela não expirar.
- Após **60 segundos**, a reserva expira, o slot fica disponível e o token anterior é invalidado. `LEAVE` explícito libera imediatamente; desconexão imprevista reserva.
- A credencial é **rotacionada em cada retomada**. Se o servidor reiniciar e apresentar outro `session_id`, o cliente invalida o segredo da sessão antiga e cria uma nova entrada (caso haja espaço na nova sala).
- Compatibilidade retroativa: clientes EHL8 que usam JOIN puro continuam aceitos com resposta de 1 byte, **sem** novo contrato. Clientes novos exigem resposta estendida para usar a retomada.
- `PLAYER_LIST` e contador da interface mostram apenas participantes **conectados**; vagas temporariamente reservadas contam para o limite máximo de 2, mas não são apresentadas como jogadores conectados. Ainda falta interface visual específica de “vaga reservada”.

### Ciclo de vida do cliente nativo

- Após JOIN estendido, C armazena o segredo somente na memória do processo. `close` ou falha definitiva limpam o segredo e PIN de memória.
- Perda inesperada de TCP causa tentativa de recuperação com intervalo de aproximadamente **1,75s**, limitada a 60s; processo de jogo e save local continuam executando sem bloquear o loop de frames.
- Heartbeat EHL8 enviado a cada **10s independentemente** das poses (~10 Hz), corrigindo a possibilidade anterior de heartbeats permanentemente adiados. Sem resposta por ~35s, o cliente inicia reconexão. O avatar remoto desaparece durante o período sem estado válido e retorna após nova pose.
- Retomar JOIN cancela a contagem de recuperação mesmo que a sala tenha reiniciado e ainda esteja aguardando outro participante; não encerra prematuramente uma partida na fila de lobby.
- **Ainda não implementado:** reconectar após fechar o jogo inteiro (o token é apenas em memória), resgate após expiração, migração de host, reserva em servidor substituído, autenticação forte para WAN, garantir operação de batalha/troca durante queda ou reinício. Não chamar esses cenários de recuperados.

### Critérios de QA adicionados

1. Teste TCP Linux/Windows para reserva, token incorreto, segredo rotacionado, liberação por `LEAVE` explícito e prazo expirado.
2. Integração de **dois processos nativos C** com servidor Python, desconectar à força apenas um e observar que retorna ao **mesmo slot** sem modificar um save.
3. Builds completos Windows x86 e Android ARMv7; verificação de regressão LAN P2P e framing C99; não desativar o auditor de SDL.
4. Somente após CI aprovado, gerar candidato beta cujo manifesto `SOURCE_COMMIT` seja **igual ao commit testado**; preservar instalador v0.8.2 estável e os perfis da PREVIEW.
5. QA no hardware do usuário: host servidor + 2 Emeralds com saves copiados; tirar o Wi‑Fi de um jogador por aproximadamente 5–10s e confirmar retorno ao mesmo mapa/slot; repetir próximo a 60s, observar aviso de falha se exceder; garantir que saves e Quest UI não mudem.

**Fonte de rollback:** branch `feature/lan-v0803-dedicated-session-core` commit `849929db684ca651abe8308878e3cba03837febb` (preview EHL8 sem esta extensão) e, para jogo Windows já validado pelo usuário, `feature/lan-v080-mega-desktop-polish` (`3f94a665bc742d2130a856b5b153596def8445a4`). Nenhum .sav foi aberto neste desenvolvimento.
