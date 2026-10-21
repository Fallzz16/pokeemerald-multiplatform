# Pokémon Emerald Hybrid — M3.1: Sala confirmada no jogo e START sem expulsão

**Data:** 21/10/2026  
**Branch isolada:** `feature/emerald-m31-room-state-ready-20261021`  
**Base exata:** PR #50 `feature/emerald-m31-ready-control-20261021` SHA `1a052dd1f42694874e4b4fa09ee251b69125cde8`; PR #50 baseado em PR #36.  
**Área:** APENAS MULTIPLAYER do Emerald existente. Não alterar .sav, mapa, história, NPCs, Pokédex, equipes ou Cable Club SIO. QA Lab é EXCLUSIVAMENTE para testes; o launcher normal oferece criar/entrar. Os PRs #38/#40 são linhas alternativas do mesmo READY (F5), **NÃO fazer merge automático** com esta linha F7.

## Problemas auditados e correções reais

1. **Corrida READY/START:** se o host autorizasse START enquanto um cliente já tinha enfileirado `READY=0`, mas o servidor processasse o cancelamento em `stage=GAME`, o código base expulsava o jogador. Agora o servidor aceita `READY=0` de atraso como **no-op** apenas durante GAME; uma carga READY inválida continua proibida e causa desconexão. Em LOBBY, `READY=0` continua cancelando normalmente e impedindo START. `READY=1` em GAME é reconhecido como ACK idempotente, inclusive após JOIN tardio, e pode atualizar lista.
2. **Estado da sala dependia da intenção local:** no PR #50, o HUD de F7 mostrava apenas o valor do botão local sem confirmação do servidor; o jogo não recebia nem interpretava PLAYER_LIST. Agora `src/lnet/lnet_session_client.c` **decodifica e valida a lista completa**: count 0–2; cada entrada com slot distinto 1/2, flag READY 0/1, nome de tamanho 1–48 e limites exatos sem bytes residuais. Só registra estado após validação de todo o pacote. Nomes não aparecem no HUD, e nenhum PIN/token/save é exposto.
3. **Entrada/saída visível no próprio Emerald:** `PortLanDedicatedRoomStatus()` em `src/link.c` repassa **somente números e o ACK do próprio jogador na game thread**. `src/platform/sdl2.c` comunica esses números ao renderer por `SDL_atomic_t`; enquanto espera START, o overlay SDL2 mostra `JOGADORES 0/2,1/2,2/2`, `PRONTOS 0/2,1/2,2/2`, e `PRONTO PARA JOGAR` ou `PRONTO CANCELADO` conforme o ACK do servidor. O texto `AGUARDANDO SERVIDOR` aparece quando não existe snapshot ou F7 foi pressionado mas ainda não chegou resposta confirmada. Após START, as mensagens de sala somem. Offline e Cable Club não ativam a UI. F6 turbo permanece preservado e F7 é o botão de sala.
4. **Testes reforçados:** `tests/test_ehl8_m23_host_start.py` reproduz cancelamento após START seguido de heartbeat e recusa pacotes inválidos. Novo `tests/test_ehl8_confirmed_room_parser.c` testa cenários válidos, rejeição de slots repetidos, tamanhos inválidos e ausência de efeitos de um pacote malformado sobre a última contagem aprovada. O teste real `tests/native_ehl8_client.c` só aceita sucesso do modo `readyswitch` após observar em sockets C reais o ACK de 0/2 e depois 2/2, com servidor Python EHL8 real. `tests/test_ehl8_wait_overlay.c` testa desenho de sala e estado aguardando, com assert de limites do viewport.
5. **Proteção legado:** `scripts/verify_v080_profile_patch.py` atualiza a reversão **exata** somente dos fragmentos novos em `src/platform/sdl2.c` e mantém a comparação por hash do código legado. Nenhum bypass da verificação histórica. `.github/workflows/emerald-auto-qa.yml` compila o teste C adicional no Linux. Saves não sofreram alteração byte-a-byte nesta revisão.

## Critérios de aceite para gameplay real

O usuário deve usar o ZIP Windows desta branch somente **depois de verificar CI e SHA** e extrair numa pasta nova. Usar saves descartáveis QA_A e QA_B. Não abrir portas públicas para EHL8; LAN privada ou VPN privada autorizada.

1. Launcher de anfitrião `CRIAR SALA`; no segundo Windows/instância `ENTRAR NA SALA` via IP privado, porta e PIN. Ambos carregam automaticamente só quando START ocorre (controles bloqueados antes).
2. Observar na janela do Emerald `JOGADORES 1/2` quando só QA_A está conectado; `JOGADORES 2/2` após QA_B. Estado PRONTOS aparece com a contagem entregue pelo servidor, não baseado em suposições de tela.
3. Pressionar **F7** em QA_A: `AGUARDANDO SERVIDOR` até ACK, depois `PRONTO CANCELADO` e `PRONTOS 1/2`. O host não deve conseguir START enquanto existir participante não pronto.
4. Pressionar F7 novamente: confirmar `PRONTOS 2/2` no jogo e no launcher. Host envia START; os jogos destravam. F7 em PLAYING não deve enviar READY=0 nem parar o gameplay. O teste de corrida rejeita kick se cancelamento previamente enviado chegar atrasado.
5. Mesmo mapa da campanha e perto da câmera: confirmar **sprite AMIGO realmente visível nas duas telas**, movimentação, diferentes mapas/esconder/reaparecer; log de transições de sprite. Desconectar/reconectar e reabrir os respectivos saves QA em modo offline.
6. Regressões: JOGAR SOZINHO não pode exibir overlay ou bloquear controles; Cable Club antigo P2P continua separado; salvar somente por mecanismo original Emerald.

**Limites honestos:** testador de C e servidor real prova wire/estado, mas **não prova** pixels, movimentação dentro de dois Emerald gráficos nem saves reabertos. EHL8 ainda não integra batalhas ou trocas do Cable Club; as trocas seguras precisarão de transação própria antes de habilitar. Android ARM64/crossplay permanece sem aceite. CI GBA `Compare` legado não equivale ao Windows nativo. PIN de seis números não protege tráfego em WAN pública.

## Rollback e PR

Não mexer em versões antigas: rollback para ZIP do PR #50 commit `1a052dd1` em **pasta isolada** sem sobrescrever saves; manter este incremento como PR draft sobre PR #50. Documentar resultados exatos de Auto QA Windows/Linux, Linux native C parser, Windows Preview (`game`, `gui-tools`, `portable`) e ID do artefato quando disponíveis. Nenhuma release ou merge até QA gráfico humano.

**Arquivo adicionado:** este documento e teste C de parser. **Arquivos modificados:** `tools/emerald_session_server.py`, `src/lnet/lnet_session_client.c/.h`, `src/link.c`, `src/platform/sdl2.c`, `src/lnet/lnet_wait_overlay.h`, `tests/native_ehl8_client.c`, `tests/test_ehl8_m23_host_start.py`, `tests/test_ehl8_wait_overlay.c`, `scripts/verify_v080_profile_patch.py`, `.github/workflows/emerald-auto-qa.yml` e `AI_README.md`. **Removido:** nada.
