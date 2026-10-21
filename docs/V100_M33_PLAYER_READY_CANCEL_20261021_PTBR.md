# Pokémon Emerald Hybrid — M3.3: PRONTO / CANCELAR dentro do Emerald

**Data:** 2026-10-21. **Branch:** `feature/emerald-m33-player-ready-20261021`. **Base de rollback:** M3.2 PR #45, SHA `b7c7c6d5556950b08ff1f6df1f5cdbce1bbfe3e7`.

## Objetivo
O jogador REAL deve conseguir ficar PRONTO e CANCELAR dentro do próprio Emerald antes de START, sem depender do QA Lab. Esta entrega usa **somente o multiplayer do jogo original** e a mensagem EHL8 `READY=0/1` que já existia. **Não altera protocolo wire, saves, história, mapas, Pokémons nem Cable Club P2P.**

## Fluxo do jogador no Windows
1. Abrir `EmeraldLauncher.exe` (NÃO QA Lab), selecionar um perfil de teste e escolher CRIAR SALA ou ENTRAR NA SALA.
2. O `pokeemerald.exe` abre e mostra a sala, inicialmente `NÃO PRONTO`. A tela informa **F9 FICAR PRONTO**.
3. Apertar F9 com o Emerald em primeiro plano. O pedido de READY=1 é enviado pelo cliente C, e o servidor EHL8 publica `PLAYER_LIST`. O painel passa a oferecer **F9 CANCELAR**.
4. Apertar F9 novamente antes de START: pedido READY=0, o botão **INICIAR PARTIDA** no launcher do host desabilita; o outro cliente acompanha o contador de prontos real.
5. Quando ambos enviarem READY=1 e a lista mostrar 2/2 prontos, o anfitrião usa **INICIAR PARTIDA** no launcher. START desbloqueia os controles e encerra o overlay de espera. Depois do START, F9 não interfere na partida.
6. Queda/reconexão usa READY=1 obrigatório para sessão em GAME, mesmo que a entrada original tenha sido manual, para não gerar uma desconexão falsa. Após conexão perdida o jogador continua localmente como na M3.1.
7. **Modo offline, modo clássico P2P e QA Lab permanecem com controles e automação anteriores.** Os binários do Lab que não recebem `--session-manual-ready` continuam enviando READY automaticamente, para não quebrar regressões antigas.

## Implementação
- `src/lnet/lnet_session_client.c/.h`: flags privadas de manual-ready e estado desejado, inicial READY=0 para opt-in; `lnet_session_client_set_manual_ready()` somente durante construção pré-poll; `lnet_session_client_toggle_ready()` somente em WAIT_START; fila não bloqueante de READY=0/1 com prioridade sobre heartbeat quando muda. Default antigo continua READY=1. Retomada de sessão já em GAME envia READY=1.
- `src/link.c`: expõe duas chamadas seguras somente da game thread; sem tocar saves ou SIO Cable Club.
- `src/platform/sdl2.c`: novo flag `--session-manual-ready` só é aceito se `--session-wait-for-start` também estiver habilitado; F9 (sem autorepeat) é capturado pela thread SDL2 e passado à game thread por contador atômico; a engine EHL8 envia o pedido, enquanto teclas GBA continuam bloqueadas até START. Valores locais da UI via atomic; nenhum ponteiro de socket é lido na thread SDL. Usar F9 apenas na sessão Windows/EHL8; Android ARM64 não está integrado.
- `src/lnet/lnet_wait_overlay.h`: faixa curta contextual `F9 FICAR PRONTO` / `F9 CANCELAR` no viewport existente 240x160.
- `tools/emerald_launcher.py`: opt-in **apenas no modo dedicated do jogador**, explicado em cards/convites/status. `tools/emerald_qa_lab.py` não alterado.
- `scripts/verify_v080_profile_patch.py`: dez inversões exatas das adições/modificações SDL2, verificadas byte a byte contra base M3.2, preservando a comparação de hash histórico.
- `tests/native_ehl8_client.c`: modos `manualready` e `manualcancel` testam transições reais 0→1 e 0→1→0→1.
- `tests/test_ehl8_native_bridge.py`: 2 clientes C nativos ↔ servidor EHL8 Python real com START do host; exige recusa de START quando pelo menos um não está pronto.
- `tests/test_emerald_launcher.py`: verifica `--session-manual-ready` apenas no modo dedicado real, não offline/P2P.
- `tests/test_ehl8_wait_overlay.c`: renderiza contexto F9 e garante pixels dentro de 240x160.
- `.github/workflows/emerald-auto-qa.yml` e `.github/workflows/build-v100-m23a-server-first-windows.yml`: acionamento para `feature/emerald-m33-*`.

**Novos arquivos:** este documento; nada foi removido. **Modificados:** clientes nativos, SDL2, link bridge, launcher real, testes, workflows, verificador, AI_README. **Não alterados:** servidor Python EHL8, QA Lab, save manager, P2P, mapas, Android, scripts/eventos de campanha.

## Testes exigidos
- Auto QA **Windows + Linux** no commit de código final, especialmente dois testes reais: `test_native_player_controls_ready_before_host_start` e `test_native_player_can_cancel_ready_then_confirm_again`.
- Windows Complete Preview do HEAD final: jobs `game`, `gui-tools`, `portable` e artefato extraível de SHA exato. CI de GBA Compare legado é um gate separado.
- **QA HUMANO** ainda exigido para F9 em duas janelas Windows, botão START desativando/ativando, HUD legível, controle retornando após START, mapas/sprites, reconexão e saves isolados reabertos.
- Validar F9 fora do EHL8, offline/P2P: não pode interferir. Validar QA Lab antigo: auto-ready permanece. Não chamar beta completa só por CI automatizado.

## Segurança/limites
Servidor PIN curto é LAN/VPN privada, NÃO acesso público à Internet. F9 não cria batalhas, trocas ou qualquer modificação Pokémon/save. 2 jogadores Windows primeiro; Android ARM64/crossplay e quatro jogadores são marcos futuros.

**Rollback:** pacote M3.2 PR #45 commit `b7c7c6d5556950b08ff1f6df1f5cdbce1bbfe3e7`, baixar/extrair em pasta separada. Nunca sobrescrever arquivos de save pessoais. PR DRAFT e sem merge até QA humano.
