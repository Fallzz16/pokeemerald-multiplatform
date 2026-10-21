# Emerald Hybrid M3.1 — PRONTO / CANCELAR pelo jogador dentro do Emerald

**Data:** 21/10/2026  
**Base protegida:** PR #38 `feature/emerald-m31-lobby-in-game-20261021`, SHA `90bf184b936ebbd82739d0b599d729eda10f4bdf` (Windows + Auto QA verificados no PR pai).  
**Nova branch:** `feature/emerald-m31-player-ready-toggle-20261021`. Nova PR em **rascunho**, em cima do PR #38, sem mesclar.  
**Escopo:** exclusivamente multiplayer EHL8 do Pokémon Emerald já existente. **QA Lab é ferramenta de testes**, não interface pública. Sem alterações de missões, mapas, Pokémon, saves, histórias ou Cable Club antigo.

## Problema no jogo real

O PR #38 passou a exibir JOGADORES e PRONTOS na janela do Emerald, mas o cliente sempre enviava `READY=1` automaticamente ao entrar. Uma pessoa não conseguia **cancelar a prontidão** enquanto esperava, a menos que encerrasse o jogo. As decisões históricas pedem lobby com todos prontos e START apenas com autorização do anfitrião. O servidor Python já implementava `READY=0/1`, `START` manual e atualização `PLAYER_LIST`; faltava controle no cliente nativo e interface de jogador.

## Implementação concreta

1. **F5 no Emerald enquanto está aguardando START:** a thread SDL2 registra um pedido `SDL_atomic_t` e a thread do jogo consome o pedido. A thread de eventos SDL **NUNCA** escreve diretamente no socket, no estado de save ou na thread de gameplay. Nenhuma tecla GBA original foi reaproveitada. Fora de `--session-wait-for-start`, não há efeito. Durante jogo iniciado, reconexão ou falha, F5 não manipula READY.
2. **Cliente nativo:** `lnet_session_client_toggle_ready` alterna o último estado desejado, usando **o pacote `EHL_READY` do protocolo existente**, com payload 0 (CANCELAR) ou 1 (PRONTO). Aguarda drenagem de frame anterior antes de enviar, priorizando comando do jogador sobre heartbeat/pose. JOIN ainda envia READY=1 inicialmente para preservar compatibilidade e testes antigos; F5 permite cancelar explicitamente em seguida.
3. **Servidor é a autoridade:** o host não consegue START se qualquer jogador cancelou prontidão (`start_ready_room` já exigia os dois prontos). Quando um jogador volta a PRONTO, o servidor publica um novo `PLAYER_LIST` e permite ao anfitrião START.
4. **Seu próprio estado real, sem nomes:** parser já validado de `PLAYER_LIST` agora também identifica, em memória, somente o READY correspondente à **sua própria slot** (atribuída via JOIN). `lnet_session_client_local_ready` informa essa confirmação, ou “desconhecido”, nunca dados de outro perfil. UI sincroniza pela `SDL_atomic_t` existente, com bits adicionais para confirmação e estado.
5. **Interface do jogo:** o painel agora informa **“F5 CANCELAR PRONTO”** ou **“F5 FICAR PRONTO”** conforme o último `PLAYER_LIST` confirmado, e antes da resposta mantém **“F5 ALTERAR PRONTO”**. Mostra a contagem de JOGADORES/PRONTOS. Usa bitmap SDL2 simples, dentro de 240×160. Após START, o painel desaparece e F5 deixa de alterar a sala.
6. **Launcher do jogador:** tela **COMO CONVIDAR** passa a explicar F5 e que o START ocorre apenas depois de 2/2 prontos. EHL8 host, offline e Cable Club legado continuam separados.

### Código e testes

- **Modificados:** `src/lnet/lnet_session_client.c/.h`, `src/link.c`, `src/platform/sdl2.c`, `src/lnet/lnet_wait_overlay.h`, `tools/emerald_launcher.py`, `tests/native_ehl8_client.c`, `tests/test_ehl8_native_bridge.py`, `tests/test_ehl8_player_list_parser.c`, `tests/test_ehl8_wait_overlay.c`, `scripts/verify_v080_profile_patch.py`, `AI_README.md`.
- **Adicionado:** este documento. **Removido:** nada.
- **Sem mudanças:** protocolo EHL8 no fio, servidor Python, QA Lab, saves, P2P/SIO, mapas, conteúdo, APK Android/ARM64.
- **Unidade C:** alternância permitida somente em `WAIT_START`, rejeitada em `PLAYING` e `RECONNECTING`; parser não aceita mensagens de lista malformadas e preserva READY local verificado.
- **Integração REAL de sockets C+Python:** `test_ready_cycle_native_clients` compila dois clientes C nativos; um cancela READY, o host tenta START e **deve ser recusado**; depois o cliente restaura READY e START funciona. A ponte troca poses após partida. Teste de socket **não é gameplay gráfico**.
- **Overlay:** teste C verifica bounds 240×160, painel somente em EHL8 e ambos os textos conforme READY local. O verificador do SDL2 reverte **somente** trechos exatos e preserva hash do código legado: sem desligar gates de segurança.
- **CI:** consultar **Auto QA Windows/Linux**, Windows Complete Preview `game/gui-tools/portable` e artefatos no **HEAD final** antes de anunciar download. O `CI` legado GBA `Compare` historicamente falha; distinguir da compilação Windows.

## Roteiro de QA humano da nova versão

1. Extraia o novo ZIP do PR em **pasta nova**. Preserve o ZIP anterior do PR #38 para rollback e todos os saves pessoais. Use dois **saves QA independentes**, nunca os pessoais.
2. No **launcher real**, selecione um perfil, **CRIAR SALA** e confirme que seu jogo abre e o launcher ainda permite INICIAR PARTIDA. No outro PC/instalação, **ENTRAR NA SALA** usando IPv4 privado, porta e PIN. Não use QA Lab para avaliar a experiência final.
3. Confirme painel em ambas janelas: JOGADORES 2/2 e PRONTOS 2/2, com texto **F5 CANCELAR PRONTO**.
4. Pressione **F5** em QA_B/cliente: espere atualização do servidor; ambas janelas devem mostrar PRONTOS **1/2**, a janela do jogador deve oferecer **F5 FICAR PRONTO**. INICIAR PARTIDA do host deve continuar **desabilitado**.
5. Pressione **F5** novamente, aguarde voltar para PRONTOS **2/2**, clique INICIAR PARTIDA e confirme que o painel some e os controles desbloqueiam.
6. Teste F5 depois do START: não deve cancelar a sessão. Teste jogo offline e Cable Club: nenhum painel EHL8 nem interferência.
7. Com ambos em mesmo mapa e próximos, teste sprites/movimentos em ambas direções e mudança de rota, depois queda/reconexão e reabertura dos saves offline. **Essas etapas não foram comprovadas pela IA**.
8. Se alguma etapa falhar, guardar `logs` sem PIN/perfis identificáveis, screenshot, versão/commit, e manter o PR em rascunho.

## Limitações deliberadas

Não há ainda menus internos nativos de GBA com cursor, convites PvP, batalha/troca dentro da sala EHL8, duplicação de mundo, proteção de Internet pública, ARM64/crossplay, ou QA real em dois PCs. O READY inicial continua automático por compatibilidade; F5 **permite cancelar**, não torna o READY inicial manual por padrão. Só promover para release após validar o fluxo em duas instalações com saves QA reais. Conexão entre casas usa **VPN privada**, sem port forwarding para TCP EHL8.

**Rollback:** PR #38, commit `90bf184b936ebbd82739d0b599d729eda10f4bdf`; descompactar numa pasta independente, sem sobrescrever saves.
