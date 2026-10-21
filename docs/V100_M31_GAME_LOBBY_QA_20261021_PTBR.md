# Emerald Hybrid — M3.1: lobby 0/2, 1/2 e 2/2 dentro do jogo real

**Branch:** `feature/emerald-m31-lobby-in-game-20261021` • **Base protegida:** PR #36, SHA `133322b84df0bfe24d728c9a23f0fac0f82ef07c`. **Data:** 21/10/2026.

## Por que esta melhoria importa

Na versão de jogador anterior, a janela do Emerald mostrava apenas "AGUARDANDO AMIGO" enquanto o launcher host mostrava contagem/prontos. Isso induzia confusão no cliente remoto. O protocolo EHL8 **já transmite PLAYER_LIST com participantes/prontidão**, mas o cliente C ignorava os dados. Esta alteração passa a ler esse estado de forma validada e mostra a população/prontidão na janela real do jogo.

**Escopo autorizado:** somente multiplayer do Emerald atual, sem quests/Pokémon/romance de história ou mapas novos. QA Lab continua **só para testes**, separado do launcher do jogador; saves pessoais, modo offline, sprites, Cable Club P2P e protocolo no fio permanecem preservados.

## Implementação

### 1. Parser nativo EHL8 resistente a mensagens inválidas

Arquivos: `src/lnet/lnet_session_client.c/.h`.

- PLAYER_LIST: `count (u8)` seguido por `(slot u8, ready u8, nameLength u8, nameBytes)*count`, exatamente como gerado pelo `SessionServer.snapshot()` existente.
- Valida count 0..2, slot 1..2 sem duplicações, ready 0..1, comprimentos de 1..48 e fim exato da mensagem. Registros truncados, inconsistentes ou com bytes adicionais são rejeitados **antes de atualizarem o estado**.
- O cliente mantém em RAM exclusivamente `roomPlayers` e `roomReady` após uma mensagem válida; **não envia nomes de perfis ou tokens para a UI**.
- Reinicia os números ao perder a conexão; preserva as mesmas mensagens EHL8 e funcionalidades de reconexão, sem adicionar novos tipos de frame.

### 2. Exibição no jogo

Arquivos: `src/link.c`, `src/platform/sdl2.c`, `src/lnet/lnet_wait_overlay.h`.

- A game thread expõe `PortLanDedicatedLobbyCounts(int *players, int *ready)`; o SDL coloca dois números empacotados em `SDL_atomic_t`. A thread de desenho **nunca acessa diretamente a sessão TCP**.
- Enquanto espera START, o painel SALA ONLINE agora informa em português **JOGADORES 0/2, 1/2 ou 2/2** e **PRONTOS 0/2, 1/2 ou 2/2** quando os dados existem. Antes da primeira lista recebida, mantém o texto antigo de espera.
- Fontes bitmap 3×5 agora possuem dígitos e barra, sem dependências SDL_ttf/fontes externas. O viewport continua 240×160 com escala inteira do projeto.
- Após START, o painel desaparece; se a rede cair, permanece o aviso anterior de reconexão ou conexão perdida **sem bloquear o jogo local**.

### 3. Testes adicionados/ampliados

- `tests/native_ehl8_client.c`: o modo `awaitstart` requer que C nativo tenha recebido **2/2 jogadores e 2/2 prontos antes de START**, em adição ao heartbeat e ao recebimento de pose remota.
- `tests/test_ehl8_player_list_parser.c` (NOVO): invoca o parser de produção com casos válidos 0/1/2 e casos inválidos de duplicidade, limites, truncamento e ready inválido. Não lê ou altera `.sav`.
- `tests/test_ehl8_wait_overlay.c`: cobre contagem/prontidão no viewport e mantém as verificações de states offline/conectado/reconexão.
- `.github/workflows/emerald-auto-qa.yml`: compila e executa o teste C do parser no Linux, em complemento ao Auto QA da ponte nativa.
- `scripts/verify_v080_profile_patch.py`: atualiza a reversão **exata** dos cinco fragmentos SDL2 revisados para que o verificador legado de SHA original continue bloqueando mudanças acidentais.

## Aceite de entrega e limitações

| Verificação | O que realmente comprova |
|---|---|
| Auto QA Windows/Linux | Testes de parser e duas conexões EHL8 em C nativo; não pixels reais. |
| Windows Complete Preview | Compile `pokeemerald.exe`, launcher, QA Lab e pacote verificado em SHA, sem dados pessoais. |
| QA do usuário | A janela do jogo mostra 0/2→1/2→2/2, estados de PRONTO, espera pelo START, controles liberados. |
| QA mapa | Dois sprites no mesmo mapa/câmera, movimento, transição, perda/retorno sem perder saves. Pendente. |
| PvP/trocas EHL8 | Não implementado nesta alteração; sistema Cable Club P2P original continua distinto. |
| Android/crossplay | Não implementado/validado aqui; ARMv7 segue na árvore Android. |

**Não chamar de beta completa nem mesclar** antes do QA humano. O build automático não valida render real, interações, a recuperação do save, Battle/Trade, nem execução em dois PCs. Baixar apenas pacote do HEAD correto em pasta nova, usando perfis QA descartáveis.

**Rollback:** PR #36 `feature/emerald-m31-native-reliability-20261021` SHA `133322b84df0bfe24d728c9a23f0fac0f82ef07c`; não sobrescrever arquivos .sav.
