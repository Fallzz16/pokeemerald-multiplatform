# M3.1 — Confiabilidade do cliente nativo e observabilidade do multiplayer

**Data:** 21/10/2026 • **Branch isolada:** `feature/emerald-m31-native-reliability-20261021` • **Base:** PR #29 / `a4e019c5e5e84aa9bce9140db3c87b5b70477051`.

## Contrato e escopo

Usuário delegou liberdade técnica total nesta sessão, mantendo todas as escolhas anteriores. **Somente multiplayer do Emerald existente**: não adicionar narrativas, quests, mapas, Pokémon, cosméticos ou sistemas de campanha. **QA Lab/QA_A/QA_B são ferramentas EXCLUSIVAS para testar**; o launcher que jogadores veem é separado. Preservar saves locais, Cable Club P2P, jogo offline, sprites do Emerald, controles e rollback.

**Estado:** implementação em revisão/CI; este arquivo NÃO é certificado de versão beta pronta. Até evidência física em duas máquinas, não atribuir comportamento visual a um teste de socket.

## Inspeção de engenharia

Arquivos revisados: `src/lnet/lnet_session_client.c/.h`, `src/lnet/lnet_presence.c`, `src/link.c`, `src/platform/sdl2.c`, `src/lnet/lnet_wait_overlay.h`, `tools/emerald_session_server.py`, `tools/emerald_launcher.py`, workflows de Auto QA e Preview Windows, `tests/native_ehl8_client.c`, `tests/test_ehl8_native_bridge.py`, docs de arquitetura e continuidade.

**Descoberta e correção de interpretação:** o cliente C já possuía um **heartbeat genérico de reserva**, mesmo quando estava em `WAIT_START`; portanto a afirmação de que não enviava heartbeat antes de START seria **inexata**. Alteramos essa dependência implícita para uma condição **explícita e testada** em WAIT_START e PLAYING, evitando que futuras mudanças em pacotes idle a removam acidentalmente. O teste novo verifica a propriedade usando dois processos de código nativo real e o servidor real.

## Alterações de código neste incremento

### 1. Espera real no C nativo (`src/lnet/lnet_session_client.c`)

- `EHL_CLIENT_WAIT_START` agora participa explicitamente da prioridade de HEARTBEAT a cada 10 s (250 ms no teste acelerado), independentemente de transmissão de poses em PLAYING. HELLO/AUTH/JOIN/READY continuam prioritários.
- `EHL_AUTH_TIMEOUT_MS` mantém padrão 20 s, mas recebe override de compilação **apenas em binário de testes** para verificar uma espera mais longa que o timeout abreviado. O jogo publicado continua usando 20 s.
- Wire EHL8 e protocolo SIO não mudam; não envia PIN/token/saves em heartbeat.

### 2. Teste de START com C real (não mock)

- `tests/native_ehl8_client.c`: modo `awaitstart` verifica que entrou no estado WAIT_START e que não recebeu START antes do atraso esperado. Após START deve receber pose remota real e encerrar com status 0.
- `tests/test_ehl8_native_bridge.py`: compila um binário adicional (timeout de 2,3 s em vez de 20 s, heartbeat 250 ms). Cria um `SessionServer` REAL com `manual_start=True`, conecta duas instâncias C por TCP loopback, verifica 2/2 prontos, espera ~3,25 s com nenhum START, contabiliza ≥3 heartbeats no estágio LOBBY de cada cliente, autoriza START e exige troca de poses e encerramento 0.
- Isso é mais fiel que cliente simulado Python, porém **não abre as janelas GBA/SDL nem carrega saves**. O teste complementa o ensaio existente de >30 s com dois peers Python.

### 3. Aviso de perda de conexão dentro do jogo

- `src/platform/sdl2.c` acompanha estado EHL8 **após START**, sem reativar o bloqueio dos controles: 2 = conectado, 4 = reconectando, 5 = conexão falhou. O título da janela muda conforme transição. Thread do jogo publica o estado via `SDL_atomic_t`, renderizador apenas lê. Antes de START continua a tela de espera/falha original.
- `src/lnet/lnet_wait_overlay.h`: faixa visual pequena no viewport 240×160 com **RECONECTANDO** ou **CONEXAO PERDIDA / JOGO LOCAL ATIVO**, sem encobrir o jogo inteiro ou mexer em arquivos. O banner desaparece na reconexão; não aparece em modo offline/P2P. O tempo de reconexão permanece 60 s segundo token e servidor.
- `tests/test_ehl8_wait_overlay.c`: cobre estado 4/5, retorno a 2 (sem banner), coordenadas dentro da tela e estado offline sem HUD.
- `scripts/verify_v080_profile_patch.py`: substitui exatamente os **três fragmentos antes allowlistados** que mudaram em SDL2, mantendo intacta a lógica antiga de hash/rollback do código legado, sem desativar verificações.

### 4. Logs úteis para detectar sprite remoto

- `src/link.c`: registra somente transições reais de sprite EHL8 (spawn com ID de mapa, remoção por mudança de mapa/desconexão, saída de câmera) no log local. **Não registra PIN, nomes de perfil ou saves**. Os eventos são de transição, não um log a cada frame.
- Se o jogador não vê seu amigo, esses registros ajudam a distinguir falha de rede da etapa de criação/culling de sprite. O log **não é substituto de prova visual**.

### 5. CI ativado para nova branch

- Workflows `.github/workflows/emerald-auto-qa.yml` e `.github/workflows/build-v100-m23a-server-first-windows.yml` reconhecem `feature/emerald-m31-*`. Auto QA agora observa alterações do cliente C nativo. O Windows completo executa `tests/test_ehl8_native_bridge.py` antes de compilar o jogo.
- CI final e artefato devem ser verificados **pelo SHA EXATO no GitHub Actions**, sem reutilizar um run antigo.

## Pesquisa e decisão de arquitetura

- [Valve: Source Multiplayer Networking](https://developer.valvesoftware.com/wiki/Source_Multiplayer_Networking) descreve a necessidade de interpolação de entidades e tolerância a perda de snapshots.
- [Glenn Fiedler: Snapshot Interpolation](https://new.gafferongames.com/post/snapshot_interpolation/) explica atrasos curtos e buffers contra jitter; **NÃO** adotar valores genéricos de FPS/latência sem medir no grid/scroll do Emerald.
- [Python asyncio streams](https://docs.python.org/3/library/asyncio-stream.html) explica `drain()` e controle de backpressure; o servidor já usa `wait_for(writer.drain(), 2)`, então não há razão para duplicar essa proteção.
- [SDL2 integer scaling](https://wiki.libsdl.org/SDL2/SDL_RenderSetIntegerScale) confirma o método do renderer atual de manter pixels inteiros. O banner usa coordenadas lógicas 240×160 e deve respeitar o scaling já habilitado, sem reconfigurá-lo.

**Decisão:** antes de adotar interpolação baseada em buffer temporal (jitter) mais complexa, recolher evidência real de sprites, câmera e ping em duas instâncias. Evitar redesenhar em cima de sistemas que ainda não tiveram seu comportamento visual confirmado.

## Gates do novo Preview

| Gate | Critério | Estado até execução de CI |
|---|---|---|
| Código/CI | Auto QA Windows+Linux e native C real + tests overlay | **A verificar no run final** |
| Build Windows | Jobs game/gui-tools/portable, ZIP/hash, commit final | **A verificar no run final** |
| QA humano na mesma máquina | QA_A/QA_B ou dois launchers reais: antes/depois START e dois sprites visíveis | **Pendente** |
| QA de rede/recovery | Queda de um cliente, faixa reconexão e depois online/offline no jogo real | **Pendente** |
| Multiplayer em dois PCs | Presença em Hoenn, movimento nos dois sentidos, troca de rota, saves solo intactos | **Pendente** |
| Batalhas/trocas EHL8 | Convites reais e engine antiga integrados com rollback de saves | **Não implementado** |
| Android/crossplay | APK ARM64, conexão Windows↔Android, save/controles | **Não validado** |

### Teste humano seguro após build

1. Use ZIP exato da nova branch em pasta NOVA; preserve a instalação aprovada do PR #29. Use apenas perfis/saves de teste.
2. No launcher final: CRIAR SALA, segundo jogador ENTRAR, ambos 2/2 prontos, host clica START. Verifique outro sprite no mesmo mapa e movimento.
3. Após START, com ambos jogando, desconecte temporariamente o cliente convidado **apenas pelo controle de testes ou rede privada**, sem encerrar saves abruptamente. Observe faixa RECONECTANDO, remoção temporária do sprite remoto, e retorno da conexão; se a janela de 60 s vencer, faixa CONEXAO PERDIDA, mas solo continua. Em caso de erro, não usar save pessoal.
4. Confira logs de jogo/servidor: `remote sprite shown`, `removed`, `hidden outside camera` quando ocorrerem; logs são evidência auxiliar, não vídeo/print.
5. Valide retorno offline/saves em duas pastas. Se houver falha, anote passo/revisão e envie logs sem PIN/identificadores/saves pessoais.

**Rollback:** `feature/emerald-m30-player-journey-20261020` SHA `a4e019c5e5e84aa9bce9140db3c87b5b70477051` (PR #29). Nenhum arquivo `.sav`, release pública, ramo `main` ou PR anterior deve ser alterado nesta atualização.


## Continuação da M3.1 — Mapas nativos e indicador AMIGO (21/10/2026)

**Origem:** usuário pediu `Continue` com liberdade técnica, sem ampliar escopo. Esta continuação permanece no **PR #36** da mesma branch `feature/emerald-m31-native-reliability-20261021`. Base e rollback seguem PR #29 SHA `a4e019c5`. Não houve edição de saves, mapas, histórias, Pokémon, Android, servidor wire, nem Cable Club.

### Implementado agora

1. `tests/native_ehl8_client.c` recebeu modo de teste `mapcycle`: duas instâncias C autênticas atravessam mapa 0 (ativo), mapa 1 (ativo), posição inativa (sair de campo), e mapa 2 (ativo). Cada cliente exige receber do outro a sequência visível/oculta/reaparecida, sem carregar arquivos de save ou janela gráfica.
2. `tests/test_ehl8_native_bridge.py` inicia dois processos C e o servidor EHL8 de produção em TCP loopback; exige sucesso de ambos e **inspeciona no servidor** a chegada efetiva de `LANP active/mapNum` para ambos `(1,0)`, `(1,1)`, `(0,1)`, `(1,2)`. Esses códigos são *valores do teste*, não mapas criados no jogo. Não equivale a testar sprites na engine em Windows.
3. `src/link.c` expõe `PortLanDedicatedFriendInView()` somente em runtime PORTABLE, lendo sprite virtual existente, estado EHL8 PLAYING e a projeção real de câmera já implementada. Não exige consulta a saves e não muda as coordenadas.
4. `src/platform/sdl2.c` transmite esse booleano da game thread ao renderer via `SDL_atomic_t`; só no EHL8, depois de START e quando estado conectado PLAYING, desenha o novo badge pequeno **AMIGO** no topo da tela, jamais para outro mapa, offline ou conexão caída.
5. `src/lnet/lnet_wait_overlay.h` implementa o badge usando o mesmo renderer bitmap 3×5 e faixa escura sem fontes externas; `tests/test_ehl8_wait_overlay.c` acrescenta caso 0 (nenhum desenho) e 1 (desenho dentro de 240×160). `scripts/verify_v080_profile_patch.py` remove por inversão **exata** apenas os quatro deltas SDL2 dessa atualização antes da verificação hash do source legado; não abre exceção genérica.

### Evidência, correção e limites

O **primeiro** native TCP CI de mapas [run 39550575971](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/39550575971) falhou: no modo mapcycle, a ferramenta de teste retornava êxito antigo assim que recebia a PRIMEIRA pose, sem executar o ciclo. Corrigido em `tests/native_ehl8_client.c`: não encerra cedo quando `mapcycle` está ativo. [Native job 39550715423](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/39550715423) passou depois dessa correção. A inspeção adicional no servidor e o badge AMIGO são commits posteriores, portanto **exigem conferência do Auto QA + Preview Windows mais recente** antes de oferecer novo ZIP.

**O que falta comprovar com usuário:** dois trainers visíveis em Hoenn e indicador AMIGO no momento correto; hidden/reappeared após warp e menus; reconexão/latência; integridade de saves reabertos; PvP/troca por EHL8 e Android permanecem pendentes. Não mesclar PR draft nem divulgar beta final com base nesses testes de rede.
