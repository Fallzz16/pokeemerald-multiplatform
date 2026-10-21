# M3.1 — PRONTO / CANCELAR dentro do Emerald (F7)

**Data:** 21/10/2026 • **Branch:** `feature/emerald-m31-ready-control-20261021` • **Base preservada:** `feature/emerald-m31-native-reliability-20261021` SHA `8169aeafc138e79a48d86080b9fe1b4857fbe461`, PR #36. Criar PR DRAFT empilhado sobre #36, nunca mesclar automaticamente. Rollback: ZIP original do PR #36 SHA `8169aeaf` em pasta nova, sem mover ou substituir .sav.

## Objetivo restrito

Adicionar a capacidade de **confirmar/cancelar PRONTO antes do START dentro do jogo real** no protocolo EHL8 já existente, preservando todas as regras originais: somente multiplayer do Emerald atual, **não** criar mapas/quests/Pokémon, QA Lab continua fora do launcher final, salvamento solo independente e Cable Club P2P intactos.

## Comportamento visível

- Ao criar/entrar numa sala EHL8, o Emerald abre como antes e fica bloqueado até START. O cliente **continua PRONTO automaticamente**, igual à revisão anterior (compatibilidade).
- Enquanto aparece **SALA ONLINE**, uma pequena faixa mostra `PRONTO PARA JOGAR` e `F7 ALTERAR`.
- Pressionar **F7** uma vez passa a **PRONTO CANCELADO** e envia `READY=0` pelo TCP EHL8. O botão `INICIAR PARTIDA` do anfitrião deve ficar desabilitado enquanto houver alguém não pronto.
- Pressionar **F7** outra vez envia `READY=1`; depois de ambos prontos o anfitrião pode iniciar normalmente. O jogo fica desbloqueado somente pelo START verdadeiro do servidor.
- **F6 segue sendo TURBO**, sem qualquer modificação de função. Offline e modo clássico Cable Club não capturam F7 para READY nem mostram o painel.
- F7 é tratado pela thread SDL de entrada como mudança de um `SDL_atomic_t`; apenas a **game thread** lê o valor e pede ao cliente C para emitir mensagem de READY. Não manipular sockets do renderer ou gravar save.

## Código efetivo

- `src/lnet/lnet_session_client.c/.h`: campos `requestedReady`, `sentReady`, API `lnet_session_client_set_ready` (game thread), estado inicial 1, JOIN envia READY desejado, alterações posteriores somente em WAIT_START com a fila de pacotes TX vazia; envios HELLO/AUTH/JOIN têm prioridade. Sem alteração de versão ou bytes do protocolo.
- `src/link.c`: `PortLanDedicatedRequestReady()` somente para sessão EHL8, nunca link/SIO.
- `src/platform/sdl2.c`: F7 na janela do Emerald antes do START, mudança atômica da intenção de ready; F6/Alt+Enter/F11 e input gate originais preservados. No game thread, valor é passado ao cliente; depois do START não mexe em READY nem bloqueia controles.
- `src/lnet/lnet_wait_overlay.h`: faixa bitmap com `PRONTO PARA JOGAR`/`PRONTO CANCELADO` e tecla F7, sem recursos externos; só renderizada na sala EHL8 aguardando START.
- `scripts/verify_v080_profile_patch.py`: inversão exata dos blocos F7+SDL2 para proteger o hash original de compatibilidade; não remover/verificar menos.
- `tests/native_ehl8_client.c`: modo `readyswitch` cancela e confirma READY com o cliente C real.
- `tests/test_ehl8_native_bridge.py`: dois subprocessos nativos C, servidor Python EHL8 real em modo START manual, exige 2/2 inicialmente, depois 0/2, recusa START, recupera 2/2, autoriza START e observa poses bidirecionais. Não lê saves.
- `tests/test_ehl8_wait_overlay.c`: verificações do painel `PRONTO` e `CANCELADO` sem desenhar além de 240×160.

## Testes e gates

**Importante:** pipeline completa Windows/Linux e ZIP **ainda devem ser verificados por SHA exata desta branch**, sem reutilizar CI do PR #36. O primeiro Auto QA intermediário [39552103883](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/39552103883) falhou em Linux porque o novo renderer READY ainda não tinha sido chamado no teste C, causando `-Werror=unused-function`; foi corrigido imediatamente adicionando os dois testes. Checar novo run após a correção.

**Aceite real no PC:**

1. Baixar ZIP aprovado da branch em pasta separada, selecionar saves de TESTE, abrir launcher do jogador e CRIAR SALA / ENTRAR NA SALA. QA Lab não deve ser necessário.
2. Aguardar 2/2 prontos. Antes de START, pressione **F7** em um dos jogos. O overlay deve mudar para PRONTO CANCELADO e o launcher do host deve mostrar 1/2 prontos/desabilitar botão.
3. Clique START na condição 1/2: NÃO deve iniciar. Pressione F7 de novo, espere 2/2, clique START: controles liberados nos dois jogos, painel some.
4. Verifique que F6 continua turbo após START, modo offline sem painel, P2P sem regressão.
5. Ambos no mesmo mapa, marca AMIGO e movimento bidirecional. Reconexão e saves em dois PCs físicos precisam de QA separado.

**Pendências reais:** renderização humana, segunda máquina, EHL8 batalhas/trocas e transações seguras, ARM64/crossplay, logs/latência reais; não chamar beta completa antes de comprovar estes gates. Nenhuma alteração em .sav, mapas, scripts de história, sprites originais, Android ou ROM GBA neste incremento.
