# Emerald Hybrid Multiplayer — arquitetura e especificação v0.8.0+
**Estado: planejamento aprovado em parte; sistema dedicado de quatro jogadores ainda NÃO implementado.**
**Base:** `feature/lan-v0721-viewport-culling`.
**Documento companheiro de continuidade:** [../AI_README.md](../AI_README.md).

## 1. Objetivo do produto

- Mesmo aplicativo oferece **Jogar offline / Hospedar / Entrar** no Windows e Android.
- O host pode jogar ou usar aparelho extra como **servidor dedicado**, incluindo cenário: três celulares (um servidor, dois jogadores).
- Servidor dedicado é **núcleo leve de rede e sessão**; não carrega `AgbMain`, nem mapas, gráficos ou saves.
- Até **quatro jogadores na sessão total**, contando host jogável; o jogo é nativo, preserva saves e história individuais, e exibe apenas os jogadores presentes no mesmo mapa/câmera.
- Inicialmente LAN Wi-Fi ou hotspot com descoberta automática + IP manual; Internet é futura e depende de novo modelo de segurança.
- Jogadores em versões incompatíveis não entram. O launcher deve oferecer atualização quando tecnicamente viável e devidamente verificada; atualizar código não é função do protocolo de gameplay.

## 2. Registro EXAUSTIVO das respostas do usuário 1–75

Estas decisões foram expressamente escolhidas, não inferências de como o código já funciona:

| Nº | Escolha | Decisão |
|---|---|---|
| 1 | B | Host jogável **e** servidor dedicado. |
| 2 | A | Windows e Android podem hospedar. |
| 3 | B | Alvo até quatro jogadores, integração começa com dois. |
| 4 | B | Servidor Android inicialmente com tela ligada; modo background depois. |
| 5 | B | LAN agora, internet futuramente. |
| 6 | C | Descoberta automática + IP manual. |
| 7 | A | Porta 45680 padrão, configurável. |
| 8 | B | Lobby, seleção de save, todos prontos, administrador inicia. |
| 9 | A | Entrada tardia permitida após início da aventura. |
| 10 | A | PIN ou senha configurável para a sala. |
| 11 | A | Painel admin: ver, expulsar, encerrar. |
| 12 | B | Perda do host: continuar local/offline, com reconexão quando possível. |
| 13 | B | Múltiplos perfis de save. |
| 14 | B | Exibir treinador, aparência, equipe, insígnias, localização e tempo de jogo. |
| 15 | A | Importar saves Emerald .sav compatíveis com validação/backup. |
| 16 | A | Saves em cada dispositivo; servidor não é repositório dos saves. |
| 17 | A | Pessoas com progressos diferentes se encontram em mapas acessíveis a ambas. |
| 18 | A | Novo jogador começa em Littleroot e faz introdução normal. |
| 19 | A | NPCs/eventos de história locais. |
| 20 | B | Exploração visível + interação com A, em etapas. |
| 21 | A | Batalhar, trocar, ver perfil. |
| 22 | A | Batalhas selvagens individuais. |
| 23 | C | PvP e cooperativo, incrementos separados. |
| 24 | A | Sem colisão obrigatória entre jogadores. |
| 25 | C | Emotes/mensagens rápidas e chat de texto; começar pelo leve. |
| 26 | B | Launcher moderno. |
| 27 | A | Android horizontal (launcher + jogo). |
| 28 | C | Controles touch personalizáveis e controle Bluetooth. |
| 29 | A | ARM64 prioritário, preservando ARMv7 quando viável. |
| 30 | A | Pequena cabeça no PokéNav indicando cidade/rota do amigo. |
| 31 | — | Meta: jogar em celulares com **4 GB+ RAM**, sujeito a CPU/OS/ABI/teste real. |
| 32 | — | Usuário testou v0.7.2.1 com dois personagens: relatou que funcionou muito bem. |
| 33 | C | App universal com servidor sem interface adicional no Windows. |
| 34 | A | Host jogável inicia servidor internamente. |
| 35 | A | Máximo de 4, inclusive host. |
| 36 | A | Batalhas por pares independentes; os demais continuam explorando. |
| 37 | A | Convite discreto para batalha/troca com aceitar/recusar. |
| 38 | A | Entrou depois: carregar save próprio no próprio local, sem teleportar. |
| 39 | A | Mesmo perfil de save funciona offline e em qualquer servidor compatível. |
| 40 | A | Rejeitar segundo login da mesma identidade de save enquanto o primeiro estiver ativo. |
| 41 | B | Importação segura + backups automáticos recuperáveis. |
| 42 | A | Interação adjacente com A. |
| 43 | C | Regras de duelo livre/competitivo combinadas entre participantes. |
| 44 | A | Respeitar áreas desbloqueadas pelo progresso individual. |
| 45 | B | Launcher moderno + painel rápido durante a partida. |
| 46 | A | Painel do dedicado leve: jogadores, IP, porta, status, expulsar/encerrar. |
| 47 | B | Busca automática/IP manual + QR code de convite. |
| 48 | A | Tema verde-esmeralda escuro + opção clara. |
| 49 | A | Hotspot do celular e Wi-Fi comum. |
| 50 | C | Versões incompatíveis bloqueadas, com opção de atualização segura pelo launcher. |

### 2.1. Decisões adicionais 51–75 (resposta de 25 alternativas)

O usuário respondeu às perguntas numeradas 51–75 com a sequência `1C 2A 3A 4C 5A 6B 7A 8C 9B 10A 11A 12C 13C 14A 15A 16C 17A 18A 19A 20B 21A 22A 23B 24A 25B`. **Esses números são RELATIVOS à última rodada**: `1C` equivale a `51C` (e assim por diante). Não tratar como revisão das escolhas 1–25 anteriores.

| Nº | Escolha | Decisão |
|---|---|---|
| 51 | C | Saves Windows: pasta de dados do usuário **e** opção de modo portátil ao lado do EXE. |
| 52 | A | Importar criando novo perfil sem modificar o .sav de origem. |
| 53 | A | Perfil com ID persistente fora do save, preservado na exportação; alertar para .sav importado sem metadados. |
| 54 | C | Quantidade de backups automáticos configurável pelo usuário. **O padrão 10 é recomendação anterior, não decisão expressa.** |
| 55 | A | Salvamento manual original do Emerald, com backups de segurança; **autosave não é requisito nesta fase**. |
| 56 | B | Diagnóstico de corrupção e restauração de backup, **sem reparo silencioso**. |
| 57 | A | Trocar de perfil somente após encerrar a partida e retornar ao launcher. |
| 58 | C | Android: importação/exportação via seletor de arquivos **e** pacote ZIP de backup compartilhável. |
| 59 | B | Servidor dedicado encerra por inatividade, após tempo configurável sem jogadores. |
| 60 | A | Reservar vaga por 60 segundos para reconexão após perda breve da rede. |
| 61 | A | Entrada tardia durante a sessão, com próprio save e posição; sem teletransporte. |
| 62 | C | Porta principal no modo simples; configurações avançadas opcionais de portas. |
| 63 | C | Ao fechar painel do servidor perguntar se continua hospedando ou encerra. |
| 64 | A | Alterar limite de jogadores em sessão sem ultrapassar 4 e sem remover participantes ativos. |
| 65 | A | Lista de participantes: nome, conexão e latência; **sem expor equipe/progresso por padrão**. |
| 66 | C | Batalhas entre pares: **preferir conexão direta**; retransmissão pelo servidor como fallback quando necessário. **Ainda não implementado.** |
| 67 | A | Indicar jogador “Em batalha” na lista, sem exigir indicador visual no mapa. |
| 68 | A | Poses a ~10 atualizações por segundo com interpolação; escalar só após medições. |
| 69 | A | Apenas um convite pendente por jogador; serializar/concluir antes do próximo. |
| 70 | A | **Nome SEMPRE visível** acima de cada personagem remoto na tela (difere da recomendação anterior de proximidade). |
| 71 | A | Hotspot via controles nativos do Android; app detecta rede, não precisa ligar hotspot automaticamente. |
| 72 | A | QR com IP/endereço, porta e ID da sessão; **não incluir PIN por padrão**. |
| 73 | B | PIN de seis dígitos, com limite de tentativas e mensagens de erro adequadas. |
| 74 | A | Atualização verificada e oferecida ao usuário; instalar somente após confirmação. |
| 75 | B | Compatibilidade-alvo inicial **Android 10+**; expandir depois se os testes permitirem. |

**Diferença de preferência relevante:** #70A exige nomes sempre visíveis no campo — há pouco espaço na tela nativa 240×160. Implementar rótulo compacto, recorte/posicionamento seguro, no mesmo ciclo de culling do sprite e sem sobrepor UI crítica ou derrubar FPS. Não substituir #70A por exibição só ao se aproximar sem perguntar.

**Em aberto:** decisões 76+ (p.ex., nome duplicado, medição de desempenho, retenção e proteção dos backups, controles do launcher, segurança e acessibilidade). Não preencher automaticamente como se o usuário já houvesse respondido.

## 3. Arquitetura lógica recomendada (não concluída)

```text
                    [ Emerald Hybrid Launcher ]
                        /         |           \
                   Offline    Host jogável    Entrar
                      |            |            |
               [perfil .sav]       +-----+------+----[descoberta/IP/QR]
                                   |     |
                          [EMERALD LAN SESSION SERVER]
                          host-integrado OU headless dedicado
                                   |
                         Protocolo de sessão v1
                      lobby | presença | pares PvP/troca
                              /    |     \     \
                          jogador 1   2   3     4
                             |     |     |     |
                            .sav  .sav  .sav  .sav LOCAL
```

### 3.1 Componentes e fronteiras

| Componente proposto | Papel | Proibição |
|---|---|---|
| `SessionServer` | Escutar, validar client, PIN, atribuir slot efêmero, rate limit, broadcast de presença, administrar pares | Não ler/gravar saves ou executar mapas e `AgbMain` |
| `SessionClient` | Handshake, reconexão, status, lobby, envio/recepção de snapshots, negociação de pareamento | Não manipular `SaveBlock1/2` diretamente |
| `SaveProfileManager` | Metadados, import/export, backups, seleção de perfil, isolamento Windows/Android | Nunca corrigir coordenadas de um save inválido silenciosamente |
| `Launcher` | UI Off/Host/Join, settings, lista de salas, perfis, QR e estado do servidor | Não conter parsing de SIO ou formatação direta de byte de save |
| `OverworldAdapter` | Representação N jogadores remotos e culling, sem colisão, usando sprites virtuais | Não tornar outros jogadores NPCs salvos ou replicar scripts |
| `CablePairBroker` | Estabelecer sessão SIO segura entre dois clientes, sem bloquear outros | Não assumir multiplayer GBA de 4 pessoas por padrão |

**Reaproveitamento:** `lnet_net.c` fornece sockets WinSock/POSIX; `lnet_presence.c` e `lnet_culling.c` fornecem referências de teste/projeção. Um servidor para quatro NÃO deve simplesmente compartilhar o ponteiro `LNetPresence` antigo: ele só contém um peer; projetar slots por sessão.

### 3.2 Portas e migração

**Atual P2P (não alterar):** host TCP 45680 -> cliente (link SIO); presença TCP 45681. Testado pelo usuário com dois jogadores.

**Novo modo servidor v0.8 (proposto):** porta TCP 45680 por configuração do `SessionServer` como entrada de clientes, com **framing e tipo**; retransmitir/mapear presença e iniciar **subsessões** de link entre pares, por multiplexação versionada ou segundo socket negociado. **Nunca** misturar frames do novo protocolo diretamente no mesmo TCP cru do SIO da v0.7; o handshake seria interpretado como bytes do Cable Club e falharia.

- Escolher regra concreta de compatibilidade (novo protocolo + novo cliente), número de portas auxiliares e fluxo de convites antes do código do proxy.
- Modos antigo e novo podem coexistir no produto atrás de modos/feature flags, mas não devem abrir o mesmo número de porta simultaneamente.
- Para versão da aplicação, incluir `protocolVersion`, `buildId` e `gameRulesId` (não confiar só em string de versão).
- Para internet futura, projetar criptografia/autenticação mais robusta; PIN local é apenas autorização básica dentro de rede privada.

### 3.3 Protocolo mínimo recomendado

Envelope binário independente de endianidade do host (big-endian/network order):

```text
magic[4] = "EHL8"
protocol_major:u16
protocol_minor:u16
message_type:u16
flags:u16
payload_size:u32           (limite estrito, p.ex. 4096 bytes para controle)
session_id:u64             (0 durante HELLO)
request_id:u32             (correlação/resposta)
payload[declared_size]
```

**Tipos propostos, sujeitos a revisão:** HELLO, WELCOME, INCOMPATIBLE, AUTH_PIN, JOIN, PLAYER_LIST, READY, START, LEAVE, KICK, HEARTBEAT, POSE, INVITE, INVITE_REPLY, PAIR_PREPARE, PAIR_CLOSE, SERVER_CLOSE.

**Obrigatório antes do decoder público:**
- leitura/escrita não bloqueantes com framing parcial, quotas por frame e buffers limitados;
- comprimento validado ANTES de alocação; protocolo e versão checados antes de ler payload;
- per-connection state machine: Connecting -> Hello -> Auth -> Lobby -> InGame -> Disconnected;
- isolamento de `session_id`, `player_id` efêmero e identidade de save; redaction de PIN e metadados dos saves em logs;
- replay/sequence handling para poses e rejeição de posição inválida; timeouts, backpressure e expulsão de peers malformados;
- dados de save completo **nunca** transitam pela camada de sessão;
- servidor sem autoridade sobre story/NPC/eventos; apenas sessão e coordenadas declaradas por clientes;
- distinguir rejeição de duplicação do mesmo **perfil ativo** de personagens legítimos com mesmo nome ou Trainer ID.

### 3.4 Identidade e save: não confundir conceitos

- `trainer_id` = campo herdado de Emerald, parte da identidade histórica de Pokémon/trades, não é credencial de login.
- `profile_id` = identidade persistente local/aleatória do perfil criado/importado pelo launcher, armazenada em metadados **fora do .sav**. Não é segredo de segurança por si só.
- `player_session_id` = número aleatório do jogador **nesta sessão**, emitido pelo servidor e usado para slots de rede/presença. Ao reconnect pode ser restaurado mediante token efêmero verificado.
- Identidade duplicada (40A): dois dispositivos que importam o mesmo arquivo terão mesmo conteúdo .sav, mas não necessariamente mesmo `profile_id`; decidir nas perguntas novas se o servidor detectará clone pelo **hash do save**, token/identidade importada, ou ambos. O hash muda a cada save e contém riscos de privacidade; não tratar hash bruto como identificador estável sem desenho próprio.

`SaveProfileManager` deve manter o .sav como bytes intactos e arquivos extras separados:

```text
profiles/
  <profile-id>/
     pokeemerald.sav
     profile.json        # metadados do launcher; jamais substituir jogo
     backups/
        <timestamp>_<sha256>.sav
```

**Windows:** diretório de dados do usuário preferencialmente, com migração/backup do save legado junto ao `pokeemerald.exe`. **Android:** dados privados do aplicativo + Storage Access Framework para importar/exportar arquivos via picker. Não modificar arquivo selecionado pelo usuário; copiar e validar antes de colocá-lo num perfil.

**Checksums:** Emerald utiliza setores flash de 4096 bytes e dois slots; além do tamanho 128 KiB, confirmar header/sig/counters/setores válidos. Validação não prova que story flags/map tiles estejam consistentes; nunca gerar mapas novos editando manualmente offset de save.

**Gravação segura:** a emulação atual grava a imagem inteira da flash (`FLASH_BASE`); fazer backups e cópia temporária requer rever fluxos de escrita e `CloseSaveFile`, compartilhamento de arquivos, crash entre write/rename e escolha do arquivo ativo. Não afirmar que uma simples chamada `rename()` tornou todos os salvamentos atômicos.

### 3.5 Renderização / quatro jogadores

- Receber presença de até três peers remotos por cliente (quatro participantes totais).
- Estado de cada remoto por `player_session_id`: mapa, tile, direção, sexo/aparência, atividade, sequence/recency, sprite handle. Alocar só em mesmo mapa e perto da câmera.
- Manter culling: viewport real 240×160, prefetch 32 px, retain 48 px, margens ajustáveis após QA. Sem colisão.
- Remover recursos em warp, desconexão, battle, menu, retorno offline e reconnect; não tocar NPC e save.
- A v0.7.2.1 foi aprovada visualmente pelo usuário com dois jogadores; não presume que mais sprites têm orçamento suficiente de OAM.
- PokéNav: cabeça por cidade/rota com mapeamento mapa local -> seção regional; opcional. Não extrair (x,y) do mapa diretamente como pixels do mapa de Hoenn.

## 4. Modos e UX recomendados

```text
Abrir aplicativo
  -> PERFIL [Selecionar / Criar / Importar / Backup]
  -> JOGAR OFFLINE -> iniciar jogo com save local
  -> HOSPEDAR -> [Host jogável | Servidor dedicado] -> escolher porta/PIN/limite -> lobby
  -> ENTRAR -> [Descobrir LAN | IP manual | QR] -> checar versão/PIN -> lobby
  -> [Pronto] -> Admin Iniciar -> cada cliente retoma seu próprio save
  -> Jogo -> painel rápido [jogadores, latência, convite, desconectar]
  -> Queda LAN -> notificação discreta -> continuar offline com save local
```

**Conflito de decisão resolvível:** 8B pede todos prontos para início, 9A/38A/61A pedem entrada tardia. Implementar fase de início com READY antes da primeira partida; após START, novos participantes podem entrar em uma sessão marcada como 'aceita entrada tardia', sem teleporte e sem forçar reinício dos demais.

**Lobby e administrador:** entrar depois, PIN, mostrar nome+estado, kick, encerrar. Para chat futuro, moderação e bloqueio por sessão serão decisões explícitas; não implementar coleta contínua de dados pessoais.

**Descoberta LAN:** Windows mDNS/DNS-SD compatível com Android NSD, ou fallback por broadcast local se necessário e autorizado na plataforma; IP manual sempre disponível. QR deve codificar endereço+porta e identificador de sessão, **não embutir PIN** por padrão.

**Atualizações (#50C/#74A):** comparar buildId e protocolo; download assinado/hash conferido, link oficial e confirmação do usuário; não executar atualização silenciosa. Windows e Android possuem fluxos de atualização diferentes; detalhar depois das decisões.

## 5. Roadmap revisado — marcos de aceite, sem promessa de prazo

| Marco | Entrega verificável | Saída que NÃO significa |
|---|---|---|
| **M0 — Preparação** | Documentos, decisões, parser/codec de sessão, testes fuzz/unit de protocolo, branch isolada | Não é servidor ou lobby funcional |
| **M1 — Perfis de save** | Dois perfis separados, import/export, backup+restore, launch offline Windows e Android | Não habilita multiplayer novo |
| **M2 — Session Server** | Servidor headless real em PC, depois Android foreground; dois clientes conectam e recebem status/poses | Não garante batalhas/trocas ainda |
| **M3 — Launcher e lobby** | Menu moderno offline/host/join, IP/manual+descoberta, PIN, ready/start, reconexão; save escolhido | Não garante quatro jogadores até testes |
| **M4 — 4 jogadores** | Até quatro explorando mesma rota/cidade sem perda de FPS/saves; desconexão limpa | Não sincroniza história/NPC |
| **M5 — Batalhas/trocas pareadas** | Dois em duelo/troca e demais explorando; saves corretos dos envolvidos; regressão Cable Club | Não é batalha cooperativa 4-way |
| **M6 — Polimento** | PokéNav, chat/emotes, suporte ARM64, integração Android e atualizador verificado | Não é WAN segura sem estudo |

**Primeira implementação recomendada:** M1 (perfis) ao lado de M0 (protocolo + testes); em seguida M2; só construir o UI completo em M3 sobre APIs estáveis. Os marcos podem ser versionados v0.8.0.x, mas cada release deve descrever o que realmente funciona. Não prometer tudo em v0.8.0 na primeira entrega.

## 6. Matriz de QA que bloqueia uma release

### Saves
- 2–4 perfis independentes, nomes iguais/Trainer IDs iguais, import .sav real sem alterações; arquivo intacto fora do app.
- Novo perfil sem save volta à introdução em Littleroot; perfil avançado preserva mapa, badges, Pokémon, quest e itens.
- Cópia automática antes de writes; testes de interrupção no write/recover; retrocompatibilidade .sav + export/import.
- Teste em Android de manutenção de dados ao atualizar o APK; **não desinstalar debug sem salvar a cópia**.

### Rede, lobby e servidor
- Windows dedicado e host jogável; Android dedicado (tela ligada); Windows↔Android mistos no Wi-Fi/hotspot.
- Zero, um, dois, três e quatro jogadores; limite correto (host incluído); entrada tardia e reconexão.
- IP manual; mDNS; hotspot; perda Wi-Fi; endereço IPv4 inválido; porta ocupada; firewall; PIN incorreto; version mismatch.
- Malformações: enorme payload length, frames fragmentados, frames seguidos, desconexão parcial, flooding, replay, rate-limit.
- Queda host devolve offline sem destruir save; kick limpa sprite e UI; restart server exige retorno seguro.

### Jogo e FPS
- Quatro jogadores na mesma cidade com sprites, câmera, animação, culling; rotas, warp/edifício e transições.
- Batalha entre dois e outros explorando; troca entre dois; ambos salvam/reabrem. Outros pares não interferem.
- História, quests, menus, áudio/turbo, Pokémon/OT, combate, inventário continuam Vanilla+.
- Referência de desempenho: celulares 4GB em hardware real, perfil leve e registros de frame-time/latência. Não há FPS mínimo medido validado ainda.
- Android ARM64 precisa compilar com validação de ponteiros; rodar em aparelhos 64-bit-only.

### Fonte de documentação externa para implementação
- Android NSD: https://developer.android.com/reference/android/net/nsd/NsdManager
- Android armazenamento de documentos: https://developer.android.com/training/data-storage/shared/documents-files
- Android serviços em primeiro plano: https://developer.android.com/develop/background-work/services/fgs
- Android 64-bit ABI: https://developer.android.com/google/play/requirements/64-bit
- Restrições background Android: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start

## 7. Perguntas técnicas ainda em aberto

Ver respostas futuras das perguntas 51+ antes de implementar mecanismos com efeitos irreversíveis. Temas principais:
1. Política de backup (limite, frequência e local) e falha/recuperação.
2. Identidade de perfil duplicado por dispositivos distintos, sem usar Trainer ID como credencial.
3. Política de desligar lobby/servidor e escolher perfil em tempo de jogo.
4. Discovery mDNS/hotspot e permissões Android, fallback.
5. Fluxo de atualização Windows/Android e proteção de downloads.
6. Servidor com presença autoritativa vs relé simples; anti-cheat com custo mínimo.
7. Privacidade no chat, ausência de dados pessoais/saves na rede, e exibição permanente de nomes com proteção de sobreposição na tela.
8. Handshake SIO via proxy isolado ou canal p2p negociado.
9. Android serviço foreground e suporte ARM64: fase separada de análise técnica.
10. Ordem das features antes do primeiro release usuário, limites exatos de QA.

## 8. Instruções para próxima IA

1. Ler `AI_README.md` e este arquivo **inteiros**, registrar HEAD SHA.
2. Verificar que funcionalidades existem no HEAD por arquivos reais; não declarar M1/M2 como prontas.
3. Atualizar decisão 76+ apenas com resposta explícita do usuário; registrar divergências recomendadas vs escolhidas.
4. Criar branch por marco; manter PR draft até testes automáticos/funcionais; não alterar branch anterior funcional.
5. Não entregar builds nomeados como 'completo' sem testar; nunca gerar saves com reposicionamento manual.
6. Atualizar `AI_README.md` com SHA, arquivos, testes, pendências, rollback e próximo passo **a cada atualização**.


## 9. Consequências arquiteturais específicas das decisões 51–75

### 9.1 Persistência e importação (51–58)

- Salvar no perfil selecionado em diretório próprio, sob app-data, ou em diretório portátil escolhido (Windows). Impedir que duas instâncias usem o mesmo arquivo em escrita simultânea; fornecer erro compreensível.
- Importar um `.sav` preservando exatamente os bytes de origem. Criar perfil com `profile_id` em metadados, guardar checksum e coletar nome/tempo/insígnias quando o parser suportar; nunca reescrever offsets de mapa.
- **Backup configurável (#54C)**: UI deve oferecer quantidade e política de retenção; frequência de captura nos eventos de save ainda é detalhe técnico a validar. Padrão 10 é apenas sugestão.
- Gravação manual (#55A): backup e validação sem impor autosave; conservar arquivo original, especialmente no Android.
- Exportar um arquivo .sav pelo SAF e, opcionalmente, ZIP com metadados/backups; o ZIP deve prevenir path traversal na importação e não expor arquivos de outros perfis.

### 9.2 Ciclo de servidor/lobby (59–65)

- Sessão tem períodos distintos: lobby pré-START com ready; in-game permite late join sem teleporte; 60 s de reserva para reconnect, expiração e remoção segura do sprite.
- Inatividade do servidor dedicado: timeout configurável sem jogadores, atenção para não encerrar após perda momentânea do único jogador antes do grace period.
- Admin pode alterar limite 1..4 em execução, mas nunca abaixo da quantidade de participantes atuais; ao tentar, mostrar erro contextual.
- Fechar o painel: confirmar continuar/encerrar; distinguir **fechar UI** de **terminar processo/serviço**. Android foreground permanece limitado por plataforma e etapa planejada.

### 9.3 Encaminhamento de Cable Club e nomes (66–70)

- Pareamento 1v1 simultâneo a outras explorações: o servidor negocia um socket direto temporário quando seguro/viável. Em redes/telefones nos quais não seja possível, projeto para retransmissão isolada de stream SIO por par, **sem pressupor que a latência será tolerável**. Medir handshake, slots, filas, timeout e limites por par antes de declarar fallback funcional.
- A lista de participantes sinaliza “Em batalha”; um único convite pendente por jogador; dois jogadores combatendo não devem bloquear outros.
- Poses de 10 Hz por jogador: para quatro participantes, broadcast no máximo aos outros três, com quotas. O culling visual não interrompe posição de rede.
- **Sempre renderizar nomes dos remotos visíveis (70A)**: desenhar somente quando sprite também é visível; recortar com tela e evitar nome quebrado, sobreposição com outras etiquetas, mosaico/tile budget. Ainda pendente decisão sobre ocultação manual como opção de acessibilidade.

### 9.4 Rede local e plataformas (71–75)

- Hotspot Wi-Fi pelo Android Settings; apresentar instrução e fallback IP manual se a descoberta falhar.
- QR não inclui PIN; PIN de seis dígitos e controle de tentativas. Em LAN o código é um requisito de acesso à sessão, não substitui autenticação criptográfica segura na WAN.
- Atualizações: confirmação explícita, hash/assinatura, instalação segura, recuperação se falhar, salvamento/backup antes de atualizar. Android e Windows têm processos de instalação diferentes.
- Android 10+ como alvo de versão de SO; **isso não prova ABI ARM64 ou compatibilidade geral com qualquer dispositivo 4GB**. O port ARMv7 existente continua baseline; migração ARM64 requer auditoria e QA.

### 9.5 QA adicional de aceite

1. Dois perfis com mesmo Trainer ID porém profile IDs diferentes; bloquear somente duplicidade verdadeira de perfil conforme política final de identidade.
2. Escrita local/portátil Windows, save manual, backup com retenção configurável, import/export SAF e ZIP corrompido com arquivo malicioso.
3. Queda da rede: 60 segundos de vaga reservada, reconectar antes/depois da expiração, jogador desaparece do mapa apropriadamente.
4. Host sem jogadores: timeout configurável e confirmação ao fechar painel; não derrubar sessão indevidamente.
5. Nomes sempre visíveis: quatro personagens próximos em tela de 240×160, sobreposição e culling com zoom/resize nativo.
6. PIN de 6 dígitos: repetição de tentativas bloqueada; logs sem PIN nem dados completos do save.
7. PvP entre dois com conexão direta, fallback por servidor e terceiro jogador livre; medir SIO e tempos antes de afirmar estabilidade.
8. Android 10+ ARMv7/ARM64, Wi-Fi roteador/hotspot; comparar FPS/latência em celulares com ≥4 GB de RAM.
