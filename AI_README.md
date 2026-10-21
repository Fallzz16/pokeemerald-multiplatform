# AI README — Emerald Hybrid Multiplayer: passagem de contexto entre IAs
> **LEITURA OBRIGATÓRIA ANTES DE EDITAR QUALQUER COISA NESTE REPOSITÓRIO.**
> Atualizado em 2026-10-14 (v0.8 MEGA/M2, decisões **1–116** confirmadas; estado da implementação por capítulo abaixo). Documento específico deste fork, para evitar recomeços, erros de branch, perda de recursos ou afirmações de testes inexistentes.

## 0. Resumo e fontes de verdade

- Projeto: `Fallzz16/pokeemerald-multiplatform`, port nativo de Pokémon Emerald descompilado para Windows (SDL2 x86) e Android (SDL2 ARMv7 atual).
- Histórico Vanilla+/Hybrid: Quest UI/PokéNav, turbo, áudio, QoL, Fairy, split físico/especial/status e mudanças Hybrid existentes. **Preservar sempre.**
- `README.md` principal ainda conta a fase **v0.3.4** e **NÃO é o status atual do multiplayer**. Não supor que uma branch/release contém commits de outra; verificar HEAD e arquivos reais.
- **Estado do usuário:** confirmou que o Cable Club funcionou em gameplay e que a v0.7.2.1 (personagem remoto/culling) funcionou muito bem em gameplay com dois jogadores. Isto **não é** confirmação automática de testes com quatro jogadores, servidor dedicado, lobby, ARM64, importação múltipla de saves ou migração de sessão.
- O protocolo de presença atual é **P2P para 2 jogadores**, não servidor dedicado.
- Branch com a primeira implementação/culling: `feature/lan-v0721-viewport-culling` (base para este plano).
- Branch de planejamento: `feature/lan-v080-architecture-spec`, [PR #5](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/5), criada sobre o commit base `a87e2c49e453db32def5e71ba2a2e696a911d504` (v0.7.2.1). **Esta branch é somente documentação; v0.8 NÃO foi implementada.** Verificar sempre o HEAD com `git rev-parse HEAD`; o SHA da branch muda a cada commit.
- Outras referências: `LAN_V071_QA.md`, `LAN_V072_OVERWORLD_QA.md`, `LAN_V0721_CAMERA_CULLING_QA.md`, `LAN_OVERWORLD_DESIGN.md`, `scripts/verify_lan_foundation.sh`.
- Arquitetura futura detalhada: [docs/LAN_V080_ARCHITECTURE.md](docs/LAN_V080_ARCHITECTURE.md).

## 1. Pacto inegociável de desenvolvimento

1. **Não perder ou sobrescrever saves:** nunca alterar .sav existente sem confirmação/backup recuperável; preservar a estrutura save GBA de 128 KiB e seus checksums. Um save de referência artificialmente reposicionado produziu graves tiles errados/magenta: **não usar nem distribuir os antigos saves gerados por `scripts/build_lan_qa_saves.py`**. A versão de sucesso usou um save Emerald público intacto.
2. **Não confundir relatório de CI com QA de jogo real.** Um build verde prova compilação; testes de socket não provam sprite, transição, batalha ou save in-game. Descrever evidências explicitamente.
3. **Não misturar rede de Cable Club com presença** até existir uma migração/proxy versão-controlada validada. A atual conexão principal em TCP 45680 emula palavras SIO de 16 bits; o canal de presença roda em 45681.
4. Manter comportamento **offline** idêntico ao Emerald Hybrid atual, quando recursos v0.8 não forem ativados.
5. **Progressão individual e independente**: flags, Pokédex, mapa, NPCs, equipes, inventário, missões e insígnias não são estado do servidor. Cada cliente joga do ponto e com as regras de acesso de seu save.
6. Outros jogadores são **sprites virtuais temporários**: sem colisão, sem scripts locais, sem serializar no save; aplicar culling de câmera e limpeza segura.
7. Servidor dedicado roda **sem jogo/renderização de Hoenn**; nunca embutir `AgbMain` no executável dedicado.
8. Mínimo de **4 jogadores** como objetivo de produto; iniciar integração verificável com 2 e só ampliar após testes. O host jogável conta dentro dos quatro.
9. LAN privada primeiro; **não publicar portas na Internet por padrão**. PIN de sala não substitui segurança criptográfica na Internet; planejar proteção adicional antes de qualquer modo online.
10. Para Windows x86 e Android ARMv7 manter builds/testes; ARM64 é prioridade futura e exige auditoria de pressupostos de ponteiro 32-bit. **4 GB RAM é hardware alvo, não garantia universal de FPS ou compatibilidade.**
11. Bugs: coletar logs/capturas e guardar baseline; jamais reaplicar uma correção cega. Separar release da versão experimental e abrir PR em rascunho.
12. Toda atualização/PR deve incluir atualização deste documento, sua arquitetura, **o que mudou e o que NÃO mudou**, teste automatizado + manual, riscos, rollback e novo status.

## 2. Mapa dos arquivos relevantes

| Arquivo | Responsabilidade |
|---|---|
| `src/platform/sdl2.c` | Inicialização SDL2, opções `--lan-host`/`--lan-client`, **save hardcoded `pokeemerald.sav`** em Windows e em `SDL_GetPrefPath` no Android. **É uma lacuna a corrigir para múltiplos perfis.** |
| `src/link.c` | Ponte serial SIO LAN, host/join, bombeamento de presença e desenho de um jogador remoto. Não acoplar UI nova diretamente ao handshake GBA. |
| `src/lnet/lnet_net.c/.h` | Socket TCP não bloqueante. |
| `src/lnet/lnet_link.c/.h` e `lnet_session.c` | Emulação link/handshake já testada. |
| `src/lnet/lnet_presence.c/.h` | Pacote de presença de 18 bytes, um remoto, canal TCP separado. **Não suporta quatro peers.** |
| `src/lnet/lnet_culling.c/.h` | Retângulo da viewport; 32 px prefetch / 48 px retenção e ocultação exata. |
| `src/event_object_movement.c` | `CreateVirtualObject`, `LanVirtualObjectMove` e `LanVirtualObjectDestroy`; sprites NÃO persistentes. |
| `src/main_menu.c` | Menu original Emerald; preservar até launcher externo validado. |
| `android/app/src/main/AndroidManifest.xml` | Activity launcher Android e activity do jogo; orientação, permissões. |
| `android/app/src/main/cpp/CMakeLists.txt` | Build nativo Android; atualmente ARMv7. |
| `Makefile_pc` | Build Windows x86. |
| `.github/workflows/build-lan-hybrid-windows.yml` | Build candidato Windows; não regressar artefato de saves artificiais. |
| `.github/workflows/build-lan-hybrid-android.yml` | Build Android. |
| `scripts/verify_lan_foundation.sh` | Testes nativos sessão/ligação/presença/culling. |
| `docs/LAN_V080_ARCHITECTURE.md` | Protocolo, roadmap, matriz QA, decisão por pergunta. |

## 3. Decisões aprovadas pelo usuário (1–116)

As letras são exatamente as respostas do usuário. Reconsultar a descrição de **cada uma das 100 decisões** em `docs/LAN_V080_ARCHITECTURE.md` antes de interpretar letra isoladamente. **A rodada final veio numerada 1–25 pelo usuário, mas corresponde a 51–75**; não sobrescrever as primeiras 25.

- **1–10:** 1B 2A 3B 4B 5B 6C 7A 8B 9A 10A
- **11–20:** 11A 12B 13B 14B 15A 16A 17A 18A 19A 20B
- **21–30:** 21A 22A 23C 24A 25C 26B 27A 28C 29A 30A
- **31:** objetivo de suporte a celulares com 4 GB+ RAM (**sem garantia universal**).
- **32:** usuário aprovou gameplay real da v0.7.2.1.
- **33–40:** 33C 34A 35A 36A 37A 38A 39A 40A
- **41–50:** 41B 42A 43C 44A 45B 46A 47B 48A 49A 50C
- **51–60:** 51C 52A 53A 54C 55A 56B 57A 58C 59B 60A
- **61–70:** 61A 62C 63C 64A 65A 66C 67A 68A 69A 70B
- **71–75:** 71A 72A 73B 74A 75B
- **76–85:** 76C 77A 78A 79A 80A 81A 82A 83A 84A 85A
- **86–95:** 86A 87B 88A 89A 90A 91A 92A 93A 94A 95A
- **96–100:** 96A 97A 98A 99A 100A
- **101–110:** 101B 102B 103B 104B 105C 106C 107B 108B 109C 110C
- **111–116:** 111C 112A 113B 114C 115A 116A

## 4. Ordem das futuras entregas — recomendação, ainda sujeita a novas perguntas

### M0 — desenho técnico / nenhuma mudança de gameplay
Definir protocolo session-v1 (length framing + versão + auth básica), identidade efêmera separada do Trainer ID, transições lobby -> jogo -> offline, divergência de versões e rollback. Documento + testes do protocolo em host Linux. Não mexer no Cable Club.

### M1 — perfis de save (primeira implementação concreta recomendada)
- Remover hardcode de caminho único, aceitar seleção explícita de perfil no Windows/Android.
- Validar cópia de save .sav e preservar original intacto; múltiplos diretórios/manifestos; criar novo perfil do zero sem completar intro artificialmente.
- Gravação segura: fechamento/flush corretos, escrita temporária+troca atômica quando aplicável, backups versionados e recuperação. **Não prometer atomicidade se a camada flash/OS não puder garantí-la; testar power-loss.**
- Android: Storage Access Framework (`ACTION_OPEN_DOCUMENT` e `ACTION_CREATE_DOCUMENT`), importar/exportar dentro da área privada sem pedir acesso irrestrito a arquivos.
- Testes: dois perfis separados, import/export, save/load, rollback, caminho inválido, reinício, sem quebrar modo offline.

### M2 — servidor dedicado mínimo
- Processo separado, leve, Windows/Android, sem engine/sprites/ROM.
- TCP escutando numa porta configurável, sessão com `sessionId` e `playerSessionId`, handshakes `hello/auth/compatible/ready/join/leave`.
- Duas conexões iniciais; perfil próprio por jogador; encaminhamento de snapshots com tamanho/ritmo limitado; status e timeout.
- Não confiar em nomes nem IDs de save como credenciais; não enviar `.sav` ao servidor.
- Em Windows modo headless adicional; Android modo dedicado em primeiro plano (serviço em segundo plano numa fase posterior, com análise de regras de Android).

### M3 — launcher/lobby real
- Offline/Host/Join, abas de perfis, lista de salas LAN+IP manual, porta, PIN, QR, pronto, iniciar e entrada tardia.
- Host jogável integrado ao núcleo sem exigir segundo app visível; modo dedicado sem abrir jogo; opção de voltar a modo offline ao cair.
- Painel durante jogo e painel simples de administração.
- Rede + UI desacopladas. O launcher não deve escrever internamente no formato de save em cada quadro.

### M4 — quatro jogadores/integração de gameplay
- Trocar `LNetPresence` atual (um remoto) por slots de presença versionados no servidor com até quatro membros.
- Sprites apenas em mapas iguais, camera culling e sem colisão; limites OAM; mute/ocultação, warp e desconexão.
- Interação diante do jogador, convite aceite/recusa, perfil e sessões de batalha/troca **entre pares isolados**, preservando a semântica do Cable Club. Nunca inferir que um simples relay de bytes funciona com quatro jogadores.
- Testes 2/3/4, Android/Windows cruzados, saves diferentes, batalha de par enquanto terceiros caminham.

### M5 — polimento e expansões opcionais
PokéNav com cabeças por região; chat rápido e depois texto; suporte ARM64 (auditoria/recompilação de código nativo 32-bit), emotes, multiplayer cooperativo/PvP refinados, hosting em segundo plano Android e conexão Internet apenas mediante desenho de segurança explícito.

## 5. Fatos técnicos específicos / armadilhas

- Atual `main()` Windows faz `ReadSaveFile("pokeemerald.sav")`. Android usa `SDL_GetPrefPath("EmeraldHybrid","EmeraldHybrid")` e também um único `pokeemerald.sav`. **Não existem perfis reais multi-save ainda**.
- O processo dedicado NÃO deve abrir um `.sav` GBA.
- Android possui manifest com `LanLauncherActivity` em orientação retrato, embora a escolha aprovada seja **launcher horizontal**; migrar somente após QA do ciclo de vida, incluindo intents e rotação.
- A UI nova deve ser moderna (escolha 26B) mas sem alterar os pixels originais do jogo.
- O protocolo SIO do Cable Club é sensível a latência, estado serial e tempo; preservar `SetSerialCallback(SerialCB)` no PORTABLE e não misturar slots com snapshots.
- O novo servidor não deve usar as portas 45680 e 45681 do modo P2P antigo simultaneamente no mesmo host sem um plano explícito de multiplexação ou portas distintas.
- Uma batalha PvP com regra nível 50 necessita regras negociadas, sem sobrescrever os níveis reais/salvos dos Pokémon.
- Limite de quatro não significa quatro consoles no Cable Club: modelo inicial de batalhas/trocas 1v1 pareadas.
- `README.md` antigo e documentos antigos contêm expressões do tipo "não implementado" corretas **para suas branches históricas**, não para o HEAD atual. Sempre olhar branch + commit.
- Requisitos de rede Android: NSD/mDNS possui diferenças de permissão e Wi-Fi; permitir entrada IP manual; hotspot depende do aparelho. O comportamento background exige testes reais do sistema operacional.
- Não promover versões 0.8 para main, nem dizer "pronto", sem QA em aparelhos reais.

## 6. Protocolo obrigatório para TODA atualização entregue por IA

Atualizar `AI_README.md` em cada PR/versão com pelo menos:

1. **Identificação:** branch, commit SHA, data, versão, PR/Action URLs e status (planejamento / build / jogo testado).
2. **Alterado:** arquivos, decisões implementadas e justificativas, funcionalidades novas.
3. **Não alterado / NÃO implementado:** funções excluídas do escopo, base de saves, matriz de plataforma.
4. **Testes com provas:** comando, ferramenta, resultado real, artefato/commit exato. Distinguir build, teste unitário, integração e gameplay real.
5. **Riscos e limites:** bugs conhecidos, pontos pendentes e incompatibilidades.
6. **Rollback:** último commit/branch válido e como voltar sem perder saves.
7. **Próximo incremento:** checklist priorizada de entregas verificáveis e perguntas em aberto.
8. **Alterações nas decisões:** atualizar o mapa de escolhas, com fonte e diferença de configuração.
9. **Atualizar este documento antes de chamar a atualização de concluída.**

No relato ao usuário listar, sem esconder: **adicionado / modificado / removido / testado / não implementado**. Se interrompido, retomar a partir do último SHA real, sem refazer cegamente.

## 7. Verificação / continuação para outra IA

```sh
git fetch origin
git checkout feature/lan-v080-architecture-spec
git rev-parse HEAD
git diff feature/lan-v0721-viewport-culling...HEAD --stat
bash scripts/verify_lan_foundation.sh
```

Para executar a suite nativa é necessário ambiente Linux/Windows adequado com `cc`, bash, pthread e timeout. Builds Windows e Android devem rodar no GitHub Actions e logs avaliados por SHA exato. A aprovação anterior de dois jogadores foi relatada pelo usuário; não inventar capturas que não foram anexadas.

**Decisões de produto 1–100 concluídas.** Congelar a primeira especificação de session-v1 de forma incremental e entrar em M0/M1. Evitar mais questionários gerais; perguntar apenas quando bloqueado por ambiguidade técnica real.

## 8. Registro desta atualização documental

- **Versão visada:** arquitetura de v0.8.0+, não execução do produto final.
- **Branch e PR:** `feature/lan-v080-architecture-spec`, PR #5 em rascunho; base do trabalho `a87e2c49e453db32def5e71ba2a2e696a911d504`.
- **Adicionado:** `AI_README.md`, `AGENTS.md`, `docs/LAN_V080_ARCHITECTURE.md`.
- **Modificado no gameplay:** nenhum arquivo de jogo, save, servidor, gráficos ou rede.
- **Removido:** nada.
- **Validado nesta entrega:** conteúdo documentado confrontado com decisões explícitas e arquivos-fonte da branch de origem; nenhum build/gameloop da v0.8 foi executado porque não há código v0.8.
- **Não implementado:** servidor dedicado, perfis multi-save, lobby de quatro jogadores, importador Android, auto-update, ARM64, chat, PokéNav de amigos.
- **Riscos conhecidos:** portas v0.7 P2P não são compatíveis diretamente com o protocolo futuro; Android 64 bits pede trabalho no port; proteção do save; evitar duplicar Trainer ID ou destruir identidades originais.
- **Rollback:** branch base `feature/lan-v0721-viewport-culling`; como esta PR contém apenas arquivos Markdown, basta não mesclá-la para retornar ao estado anterior. Nenhum .sav foi tocado.
- **Próximo passo:** especificação 1–100 concluída; iniciar M0/M1 em branch de implementação isolada: parser de sessão com testes e SaveProfileManager seguro, antes de ativar UI/servidor em jogo.


## 9. Registro de atualização — respostas 51–75 (documentação apenas)

- **Branch / PR:** `feature/lan-v080-architecture-spec` / [PR #5](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/5), derivada da v0.7.2.1 funcional. Confirmar HEAD do momento antes de prosseguir.
- **Pedido do usuário:** registrar suas respostas `1C 2A 3A 4C 5A 6B 7A 8C 9B 10A 11A 12C 13C 14A 15A 16C 17A 18A 19A 20B 21A 22A 23B 24A 25B` como **51C 52A ... 75B**. O usuário convidou mais perguntas e exige README para outras IAs a cada atualização.
- **Modificado:** `docs/LAN_V080_ARCHITECTURE.md` ganhou tabela 51–75 e consequências técnicas; `AI_README.md` ganhou mapa de decisões e este registro; `AGENTS.md` deverá manter contagem e obrigação de handoff atualizadas.
- **Adicionado (documentação):** requisitos de perfil portátil/normal, backup configurável, 60s de reconexão, late-join, portas avançadas, PIN de seis dígitos, nomes visíveis apenas quando próximos ou selecionados (#70B), conectividade PvP direta com fallback futuro, Android 10+ como alvo, updates apenas com confirmação.
- **Removido:** nenhum recurso do jogo, save ou protocolo.
- **Testes desta atualização:** revisão de presença e ordem das decisões, consistência da especificação e diff do PR. Não houve alteração em `.c`, build ou execução de gameplay; não declarar teste de 4 jogadores/servidor pronto.
- **Ainda NÃO implementado:** servidor dedicado, sessão de até quatro jogadores, launcher moderno, perfis multi-save, backup/restore, nomes sobre sprites, PIN, QR, ARM64, serviço Android, batalha por relé, updater.
- **Riscos:** rótulos contextuais (#70B) devem caber na viewport GBA 240x160 sem sobreposição ou queda de FPS; fallback de Cable Club por relé pode ser sensível à latência; identificar clones de save por identidade de perfil sem sobrescrever Trainer ID; Android 10+ RAM 4GB são metas, não promessa universal.
- **Rollback:** retornar à `feature/lan-v0721-viewport-culling` (commit-base `a87e2c49e453db32def5e71ba2a2e696a911d504`), que já foi validada visualmente pelo usuário. Somente Markdown foi alterado nesta branch de planejamento.
- **Próximo passo:** iniciar M0 parser/tests e M1 gerenciador de perfis em branch distinta, garantindo .sav original intacto e testes de rollback.


## 10. Registro de atualização — perguntas 76–100 aprovadas (somente documentação)

- **Data:** 2026-10-13; **branch:** `feature/lan-v080-architecture-spec`, [PR #5](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/5), derivada de `feature/lan-v0721-viewport-culling` no commit-base `a87e2c49e453db32def5e71ba2a2e696a911d504`. Consultar HEAD do GitHub antes de qualquer próxima edição.
- **Pedido:** resposta literal do usuário à rodada 76–100, novamente numerada 1–25: `1C 2A 3A 4A 5A 6A 7A 8A 9A 10A 11A 12B 13A 14A 15A 16A 17A 18A 19A 20A 21A 22A 23A 24A 25A`. Interpretar como `76C ... 87B ... 100A` — não alterar escolhas 1–25 anteriores. Não há mais rodadas gerais pendentes.
- **Modificado:** `AI_README.md`, `AGENTS.md`, `docs/LAN_V080_ARCHITECTURE.md`, com todas as decisões 1–100 e aceites M0/M1/M2/M3.
- **Adicionado (somente documentação):** nickname externo e nome original no perfil, ID persistente exportável e sessão não duplicada, save single-writer, backup após salvar manualmente, lista de restauro, modo LAN sem contas, reconexão automática até 60 s, servidor sem jogadores fecha após 15 min padrão, QR/IP manual, bloqueio temporário, rate limit de PIN, privacidade de localização PokéNav, chat opcional sem histórico, protocolo seguro de trade (a desenvolver), regras PvP acordadas, turbo seguro em link, pixel-perfect, painel Android recolhível, atualizador verificado e logs locais voluntários.
- **Removido:** nada de código, saves, UI, GBA, funcionalidades pré-existentes; nenhuma função retirada.
- **Teste realizado nesta etapa:** conferência de cada letra da rodada 76–100 contra a tabela numerada na especificação e diff GitHub para garantir alterações apenas Markdown. Nenhum build Windows/Android ou partida v0.8 foi produzido nesta etapa.
- **NÃO IMPLEMENTADO:** servidor dedicado LAN para dois/quatro clientes, PIN autenticação, lobby, gerenciador multi-profile, backups/restauração, identidade persistente, chat, painel, ARM64, suporte real de nomes de jogadores/QR no novo launcher, transações de trocas, updater. A versão jogável anterior v0.7.2.1 permanece a única fonte de gameplay validada pelo usuário.
- **Riscos:** #77A sem contas significa que um ID de perfil pode ser clonado; bloquear sessão duplicada apenas como best-effort e não confundir com autenticação. #93A troca exige fluxo comprovadamente recuperável; não anunciar atomicidade sem teste. #100A aceita primeiro **dois jogadores**; o limite final de quatro (#3B/#35A) só estará pronto depois. Metas Android 10+, 4GB RAM são alvo, não garantias.
- **Rollback:** não mesclar PR #5 ou retornar à branch `feature/lan-v0721-viewport-culling` em commit-base `a87e2c49e453db32def5e71ba2a2e696a911d504`. Nenhum `.sav` foi acessado ou modificado.
- **Próximo passo**: branch independente de desenvolvimento para M0 (framing/decoder/session states, tests) e M1 (SaveProfileManager protegido, sem integração inicial com `AgbMain`), atualização obrigatória deste README em cada PR; depois M2 servidor headless para dois clientes.


## 11. Retomada M0/M1 — testes e ferramentas (2026-10-14)

- **Branch/PR:** `feature/lan-v080-m0-m1-foundation`, [PR #6](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/6) em rascunho. Confirmar último SHA via GitHub; o primeiro commit-base deste incremento foi `7007c6704f113d102e8a80b09d13bf7ad95a6043`.
- **Adicionado:** `tools/emerald_profilectl.c`, ferramenta CLI para validar/importar/criar/backupar/restaurar/prunar perfis sem executar o Emerald. A suite `scripts/verify_lan_v080_foundation.sh` testa criação de flash apagada, rejeição de backup do perfil vazio e path traversal.
- **Modificado:** `src/profile/save_profiles.c` revalida arquivo importado **após a cópia** e backup recém-criado, excluindo uma cópia inválida; corrige limpeza de diretórios vazios em falhas ao criar perfil. Workflow Linux/MinGW verifica CLI. Atualização de documentação neste arquivo e `docs/LAN_V080_M0_M1_FOUNDATION.md`.
- **Removido:** nenhum recurso do jogo, save original, personagem, mapa ou sistema Cable Club.
- **Testes:** `bash scripts/verify_lan_v080_foundation.sh` e `SANITIZE=1 bash ...` passaram localmente após ajustes. GitHub Actions [M0/M1](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/workflows/test-lan-v080-foundation.yml) concluiu Linux com sanitizers e compilação cruzada Windows x86 com sucesso antes desta atualização documental; checar novamente status do último HEAD.
- **NÃO implementado:** selector integrado ao jogo, app gráfico, save metadata/UUID automático, Android SAF, checksums completos do save, servidor dedicado, lobby, multiplayer a quatro, PIN, QR, ARM64, trocas transacionais. Ferramenta CLI é apenas suporte de desenvolvimento.
- **Limites de segurança:** os checksums dos setores GBA ainda não são validados de ponta a ponta; lock vale somente para programas que cooperem; preservar backups antes de tocar arquivos de usuários. Não distribuir fixtures sintéticas como saves jogáveis; testes reais no jogo ainda pendentes.
- **Rollback:** para o último estado jogável aprovado, usar `feature/lan-v0721-viewport-culling` em `a87e2c49e453db32def5e71ba2a2e696a911d504`. Para somente fundação M0/M1 anterior a essa retomada, commit `7007c6704f113d102e8a80b09d13bf7ad95a6043`. Nunca sobrescrever `.sav` existente.
- **Próximo passo:** ligar escolha explícita de perfil com lock ao ciclo SDL2, resolver todos os pontos de leitura/gravação de save, testar no Windows e Android, e então iniciar SessionServer headless para dois peers. Não liberar ao público sem QA real e revisão de durabilidade.


## 11. Implementação experimental M0/M1 — integração opcional de perfis com SDL2

**Branch:** `feature/lan-v080-m0-m1-foundation`. **Base de rollback:** `feature/lan-v0721-viewport-culling` aprovada em gameplay, commit `a87e2c49e453db32def5e71ba2a2e696a911d504`. Conferir sempre HEAD e PR de implementação antes de continuar.

### Adicionado
- `src/lnet/lnet_session_v1.{c,h}`: envelope EHL8 v1 com header 28 bytes, payload máximo 4096, parsing incremental validado, sem rede TCP ou autenticação ainda.
- `src/profile/save_profiles.{c,h}`: núcleo de perfis independentes; importação sem alterar a origem, perfis blank, lock interprocessos, backup/restauração/prune; **ver limitações abaixo**.
- `tests/test_lnet_session_v1.c`, `tests/test_save_profiles.c`, `scripts/verify_lan_v080_foundation.sh`, `.github/workflows/test-lan-v080-foundation.yml`.
- `docs/LAN_V080_M0_M1_FOUNDATION.md`: documentação detalhada do código, testes, limites e rollback.

### Modificado
- **`src/platform/sdl2.c`**: aceitou `--profile-root=<diretorio> --profile-id=<identificador>` com **ambos obrigatórios** para seleção. Bloqueia o perfil antes do início e mantém bloqueio até após fechar arquivo; `ReadSaveFile`, `Platform_ReadFlash` e gravação existente referem-se ao mesmo `sActiveSavePath`. Perfil inexistente/ocupado/argumentos incompletos resultam em erro, nunca fallback silencioso para outro save. **Sem switches mantém `pokeemerald.sav` anterior**.
- Workflows candidatos Windows/Android: branch experimental adicionada a gatilhos; testes específicos de caminho/lock na suíte M0/M1.

### Removido
- **Nada**: nenhuma alteração de espécies, mapas, NPCs, batalhas, Cable Club, Quest UI, sprites, turbo, regras ou estrutura GBA de 128 KiB. Nenhum save de usuário foi acessado.

### Testado (não exagerar)
- Suíte standalone local Linux com C99 (192 roundtrips com fragmentação, limites, flags inválidas), import/lock/backup/restore de **fixtures sintéticos não jogáveis**; compilação/execução local normal e ASan/UBSan OK.
- GitHub Actions standalone Linux + Windows x86 cross compile dos núcleos M0/M1 passaram em runs anteriores desta branch (confirmar resultado no HEAD).
- **Não houve QA real nesta atualização** com dois jogos selecionando perfis. CI verde do núcleo NÃO prova integração GBA Windows/Android e backups durante saves.

### Riscos / NÃO IMPLEMENTADO
- `sp_validate_file` valida somente tamanho e estrutura de identificadores, assinatura e contadores dos setores. **Não verifica checksums** nem conteúdo semântico; dado estruturalmente válido pode estar corrompido.
- Backup automático **não está conectado ao salvamento manual**; é uma API offline a chamar com game parado e perfil bloqueado. Não restaurar um arquivo enquanto o jogo escreve flash.
- Ainda faltam IDs persistentes de perfil, enumeração/metadata e launcher com seleção; Android não expõe os switches no launcher atual; paths Windows não garantem Unicode.
- Sem servidor dedicado TCP real, 4 jogadores, lobby, PIN, QR, ARM64, chat, PokéNav de amigos, auto update, proxy SIO com par paralelo. **Não chamar de v0.8 jogável.**
- O modo default sem parâmetros não usa lock de perfil, para preservar o legado; duas instâncias legacy no mesmo diretório ainda poderiam acessar o mesmo save. Utilizar **pastas separadas** no baseline.
- Scripts de backup devem considerar falhas de energia/atomicidade/assinaturas de setores antes de receber selo de robustez.

### Próximos passos
1. Conferir Windows x86 e Android ARMv7 nativos no **commit exato** do PR; resolver eventuais erros antes de apresentar build para teste.
2. Criar ferramenta CLI segura para importar/criar perfis de teste e visualizar status, ou implementar esse controle no launcher, sem tocar no save original; usuário não deve editar .sav manualmente.
3. Testar com **dois saves Emerald originais íntegros**, Windows x2 e Android, incluindo perfil ocupado, salvar/reabrir, Cable Club, multi-mapa e rollback. Somente depois conectar backups pós-save.
4. Em branch separada, iniciar servidor de sessões real (`EHL8`) para 2 clientes e suas máquinas de estado, sem substituir LAN antiga.


## 12. Evidências finais da retomada M0/M1 + ponte experimental SDL2 (2026-10-14)

- **PR/branch:** [#6](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/6), `feature/lan-v080-m0-m1-foundation`; revisão do **código** aprovada pela CI em `98d3d24ab4144d9e83f1bd92ac2d16d6b74ab0ec`. Commits de Markdown posteriores não modificam o código; verificar HEAD.
- **Adicionado:** CLI developer `tools/emerald_profilectl.c` para `validate,new,import,backup,restore,prune`, verificação de cópias pós-import/pós-backup e limpeza parcial de erro; código de protocolo `EHL8` e testes M0/M1. Executável CLI foi gerado pela CI; não é launcher de usuário final.
- **Integrado experimentalmente:** `src/platform/sdl2.c` aceita `--profile-root=... --profile-id=...`; em modo opt-in, guarda lock do perfil durante a execução e lê `Platform_ReadFlash` do mesmo caminho do save. Sem argumentos, preserva modo legado, inclusive o caminho antigo. Android compila essa integração nativa mas launcher Android **ainda não fornece seleção gráfica de perfil**.
- **Não alterado:** lógica P2P da v0.7.2.1, mapas, Pokémon, scripts, flags de saves, UI antiga, batalhas/trocas do Cable Club. Nenhum .sav de usuário foi modificado.
- **Testes por SHA específico `98d3d24`:** [fundação M0/M1](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38506500365) **SUCESSO**, com Linux normal/sanitizers e cross-compile Win32 + CLI; [regressão TCP](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38506500556) **SUCESSO**; [build jogo Windows x86](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38506500373) **SUCESSO**; [build jogo Android ARMv7](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38506500408) **SUCESSO**. Builds nativos são compilados, **não QA de gameplay**.
- **CI GBA legado:** [execução](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38506500386) **FALHOU** na ROM GBA tradicional em `src/AgbRfu_LinkManager.c`, `_Static_assert` tratado como implicit declaration pelo compilador histórico `agbcc`. Não ocultar, nem relacionar automaticamente ao módulo de perfis (este é nativo). Exige investigação de baseline antes de corrigir.
- **Correção verificável:** a CI Windows antiga inicialmente falhou em guard de SDL2 porque esse arquivo passou a ter integração opt-in. Foi adicionado `scripts/verify_v080_profile_patch.py` que reverte **somente o patch aprovado** antes da checagem de hash histórico. Não é uma exceção genérica para mudanças arbitrárias; workflow Windows candidato passou depois.
- **Ainda NÃO implementado:** servidor dedicado multi-cliente, lobby, menus Offline/Host/Join modernos, UUID aleatório/manifestos, backup automático após save manual, validação checksum profunda, import/export Android SAF, duplicação protegida por identidade persistente, ARM64, até 4 jogadores. A opção de perfil é experimental e requer teste real de salvar/reabrir com arquivos **originalmente válidos**.
- **QA manual que ainda BLOQUEIA entrega estável:** duas instâncias selecionando perfis distintos, leitura+salvamento+reabertura, recusa de perfil em uso, cliente Windows/Android, backup/restore com jogo fechado, regressão Cable Club, seleção sem flags e sem conflito com pastas legadas. Não distribuir saves sintéticos dos testes como saves jogáveis.
- **Rollback seguro:** usar branch testada `feature/lan-v0721-viewport-culling` no commit `a87e2c49e453db32def5e71ba2a2e696a911d504`; não fazer merge deste PR antes de QA; manter backups dos .sav originais fora do diretório modificado.
- **Próximo passo:** importar **cópias** de saves reais previamente validados, realizar teste de round-trip do mecanismo SDL2 com dois perfis em Windows; implementar integridade de setores/metadata e backups pós-save; somente então iniciar SessionServer dedicado para 2 clientes. Atualizar este README novamente ao mudar qualquer código.


## 12. QA do perfil opt-in e auditoria SDL2 — 2026-10-14

**Código avaliado:** commit `98d3d24ab4144d9e83f1bd92ac2d16d6b74ab0ec` na branch `feature/lan-v080-m0-m1-foundation` / [PR #6](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/6) **DRAFT**. Atualizações documentais posteriores não alteram o binário até novo código.

### Resultado
- **Suíte C99/ASan/UBSan e cross-compile Win32 dos módulos:** [Actions 38506500365](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38506500365) — PASS; CLI de desenvolvimento `emerald_profilectl.exe` gerado.
- **Transporte TCP legado:** PASS — [Actions 38506500556](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38506500556).
- **Windows jogo completo:** PASS — [Actions 38506500373](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38506500373), artefato `11868265679`. A execução inicial anterior [38506140151](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38506140151) falhou **somente** porque o auditor v0.5 exigia o arquivo SDL original sem o novo recurso.
- **Correção auditada:** `scripts/verify_v080_profile_patch.py` faz inversão estrita da extensão de perfil em `src/platform/sdl2.c` **apenas quando `EMERALD_V080_QA=1`**. Os verficadores `verify_v050_split.py` e `verify_v050_fairy.py` continuam checando hash exato da versão histórica (após retirar o patch documentado), não foram desligados. Workflow Windows recebeu explicitamente essa flag; o build seguinte passou.
- **Android ARMv7 jogo completo:** PASS — [Actions 38506500408](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38506500408), artefato `11868630245`. **Este build compila o código de perfil mas o launcher Android ainda não expõe seleção de perfis.**
- **Distribuição de QA local:** ZIP `Emerald_Hybrid_v080_M1_Windows_Experimental_Seguro.zip` criado no container do chat, contendo executável Windows/SDL2 + CLI + BATs/README em português. SHA256 `5f60c0bf22d9a392f326d62ecbadfa872ddf8555708eb3b533eb0e4b6c3b6f1a`. Não é release estável do GitHub nem build de servidor dedicado. Arquivos artificiais de save **não** foram incluídos.

### Modificações adicionais neste ciclo
- `src/platform/sdl2.c`: flags opt-in `--profile-root`/`--profile-id`, lock e caminho único; nenhum comportamento de gameplay alterado deliberadamente.
- `scripts/verify_v080_profile_patch.py` adicionado; verificadores históricos adicionaram etapa de inversão controlada; fluxos Windows/Android e QA M0/M1 habilitados.
- `docs/LAN_V080_M0_M1_FOUNDATION.md` + este README atualizados; PR #6 corrigido para não alegar que SDL2 ainda não tinha integração.
- **Removido:** nada do jogo/saves anteriores.

### Pendências e riscos NÃO resolvidos
- **In-game:** não houve teste em duas instâncias real de saves distintos usando os novos parâmetros, portanto compilação verde não comprova persistência de perfis.
- **Integridade:** `sp_validate_file` é **apenas estrutural** (não verifica checksums); um save estragado pode passar no import.
- **Segurança:** nenhum auto-backup no hook do save manual; não restaurar enquanto o jogo está aberto. A ordem de parada do thread `AgbMain` e fclose deve ser revista antes de afirmar encerramento atômico; nos builds legados esse thread não possui join explícito.
- **Plataformas:** ainda não há launcher Android escolhendo perfis, ARM64 ou serviço dedicado real; não mostrar novo APK como se fizesse servidor no celular.
- **Rollback:** manter usuário no jogo funcional `feature/lan-v0721-viewport-culling`; qualquer teste v0.8 deve ocorrer em **uma pasta NOVA** e somente com cópias verificáveis de .sav. Não mesclar a PR #6 até QA real.

### Próximo passo recomendado
Usuário testa Windows M1 com 2 perfis independentes e devolve evidência de carregar/salvar/reabrir; corrigir quaisquer bugs de I/O. Depois acrescentar validação real de checksum e hooks de backup pós-save, importação/exportação SAF Android e início do servidor TCP de sessões M2. Não expandir para quatro ainda.


## 13. Início do launcher gráfico Windows v0.8 — M3 parcial, sem servidor dedicado

**Branch:** `feature/lan-v080-desktop-graphical-launcher`, criada sobre a fundação funcional experimental `feature/lan-v080-m0-m1-foundation` (último commit conhecido `e5485e74fa3607a9d647cb9cf7339085c5fed91c`). O rollback **definitivo de gameplay já aprovado pelo usuário** ainda é `feature/lan-v0721-viewport-culling` SHA `a87e2c49e453db32def5e71ba2a2e696a911d504`. Consulte sempre HEAD / workflow exatos.

**Motivo:** usuário corrigiu expectativa: precisava de LAUNCHER GRÁFICO real com `conta/perfil -> Hospedar servidor / Hospedar e jogar / Jogar com amigos`, e não só console PowerShell. Confirmar explicitamente que conta online não foi autorizada como obrigatória (#81A: LAN sem registro); modo atual é **perfil local com apelido**.

### Adicionado
- `tools/emerald_launcher.py`: launcher GUI Windows, visual escuro esmeralda, sidebar de perfis locais, criação/importação por `emerald_profilectl.exe`, armazenamento de apelido em profile.json, modos offline/host/join que executam o jogo M1 com flags de perfil. **Servidor dedicado aparece desabilitado intencionalmente:** não há processo de servidor implementado, portanto não inventar um botão que parece funcional.
- `tests/test_emerald_launcher.py`: testes de comandos offline/host/join, rejeição de rede inválida e IDs perigosos, verificação de que metadados não mudam bytes de save de laboratório.
- `.github/workflows/build-v080-graphical-launcher.yml`: Windows CI Python 3.12 + PyInstaller (self-contained `EmeraldLauncher.exe`) com execução de testes.
- `docs/LAN_V080_GRAPHICAL_LAUNCHER.md`: uso, status, QA, riscos, rollback e diferença da v0.7.2.2.

### Não alterado/removido
- Não modifica `src/`, dados GBA, SIO, protocolos, sprites, batalha, servidor, save format ou APK. Não removemos nenhuma função. O código Python apenas chama o executável e CLI da fundação, que já existiam.
- Todos os saves do usuário permanecem externos ao GitHub e não foram acessados. Ferramenta `emerald_profilectl` ainda faz validação **somente estrutural**, não checksum completo; usuários devem fazer backup.

### Testes e estado
- Testes do launcher GUI em Python via GitHub Actions, incluindo criar EXE Windows, dependem da execução da branch/commit; checar o status real antes de declarar pronto. Um pacote integrado exige baixar launcher.exe e os binários M1 reais, validar ZIP e verificar a interação no Windows.
- Ainda não houve QA real no desktop do usuário de criar dois perfis, carregar/salvar, entrar numa sessão e executar Cable Club pelo launcher. Compilação ≠ sucesso em gameplay.

### Ainda não implementado
- Servidor dedicado e lobby de 4 jogadores, descoberta LAN e QR, conta na nuvem/autenticação por e-mail, lista de membros, chat, Android UI equivalente, auto-backup pós-save, updater e sync transparente dos saves.
- O botão de servidor dedicado deve permanecer **visivelmente indisponível** até existir e passar pelos testes o binário de servidor real; não descrever como concluído em qualquer README.

### Próximos passos
- Concluir build Windows GUI, empacotar com `pokeemerald.exe`, `SDL2.dll`, `emerald_profilectl.exe` em pasta isolada, testar com saves copiados, obter feedback.
- Implementar M2 servidor dedicado EHL8 real com dois clientes, depois conectar lobby e habilitar botão; implementar Android launcher equivalente em Kotlin/Java após garantir seleção de perfis segura.
- Em toda entrega: registrar SHA, funções implementadas, não implementadas, testes/resultados, alterações e rollback neste README.


## 14. Primeira compilação e pacote do launcher gráfico Windows — 2026-10-14

- **Código do PR #8:** branch `feature/lan-v080-desktop-graphical-launcher`, [PR #8](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/8) draft. Baseline M0/M1 `feature/lan-v080-m0-m1-foundation`, rollback de gameplay anterior `feature/lan-v0721-viewport-culling`.
- **Launcher Windows real:** [Actions 38515194543](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38515194543) **SUCCESS**; artefato `11872050448`: `EmeraldLauncher.exe` Windows x64, 11.37MB sem Python externo. Testes Python locais de comandos, identidade e não edição de save passam no CI; empacotamento PyInstaller foi aprovado.
- **Jogo M1 Windows compilado no PR:** [Actions 38515194575](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38515194575) **SUCCESS**. Pacote integrado atual foi montado usando os binários previamente compilados/validados da fundação M1, não inventar que houve gameplay real novo.
- **Auditoria genérica da ROM:** [Actions 38515194315](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38515194315) **FAILURE** independente do launcher. **Android candidate:** em compilação na última verificação, não possui a nova UI/seleção de perfis de qualquer modo.
- **Pacote de teste gerado no container do chat:** `Emerald_Hybrid_v080_Launcher_Grafico_Windows_Experimental.zip`, tamanho 23.428.533 bytes, SHA256 `bab52b190bbf73d4b3171b51d26837f4be63758d85637b631091b3b2c0d0df79`. Contém `EmeraldLauncher.exe`, `pokeemerald.exe`, `SDL2.dll`, `emerald_profilectl.exe`, `PORTABLE_MODE.txt`, `LEIA_PRIMEIRO_LAUNCHER.md` e `SHA256_COMPONENTES.txt`; ZIP CRC e hashes internos verificados, sem qualquer `.sav` de teste.
- **Resultado:** visual e comandos funcionam em testes automáticos do novo launcher, **não foi validado em dois jogos reais em Windows ainda**. Usuário deve testar criar/importar perfil a partir de CÓPIA de .sav, salvar/reabrir offline, host/join, Cable Club, conexão e logs. Não há servidor dedicado: opção intencionalmente bloqueada na UI. Conta = perfil LOCAL, não credencial online. Esta atualização **não implementou nenhum dos recursos incompletos** citados na seção 13.
- **Arquivos alterados/adicionados:** source GUI e testes, workflow PyInstaller, docs. Nenhum gameplay antigo removido e nenhum usuário save editado. **Rollback:** descompactar em pasta nova e, se falhar, retornar à v0.7.2.1 salva separadamente, preservando os backups.
- **Próximo passo recomendado:** validar runtime com perfis originais, corrigir bugs de interface, implementar SessionServer dedicado real antes de habilitar a opção correspondente, depois fazer UI equivalente no Android.


## 15. Correção de distribuição: launcher avulso não abre perfis (relato do usuário, 2026-10-14)

- **Erro reproduzível pela inspeção do pacote/artifact:** usuário baixou o artefato isolado `Emerald-Hybrid-v080-GraphicalLauncher-Windows-x64-Experimental`, contendo **somente** `EmeraldLauncher.exe`, e recebeu `emerald_profilectl.exe precisa estar ao lado do launcher` ao pressionar `Criar ou importar conta`. Não é falha no save: **faltam dependências no pacote avulso**. Também faltariam `pokeemerald.exe` e `SDL2.dll` para iniciar uma partida.
- **Correção realizada nesta conversa (empacotamento, não código):** criado e validado `Emerald_Hybrid_v080_Launcher_COMPLETO_CORRIGIDO.zip`, 23.420.651 bytes, SHA256 `a440ee40e1906af20dadd323678f2161def588876d44942195c8fd6492a113f3`. O ZIP contém `EmeraldLauncher.exe`, `emerald_profilectl.exe`, `pokeemerald.exe`, `SDL2.dll`, `PORTABLE_MODE.txt`, `SHA256_COMPONENTES.txt`, `LEIA_PRIMEIRO_LAUNCHER.md`, `ABRIR_LAUNCHER.bat` (verifica componentes e inicia o launcher) e `LEIA_PRIMEIRO_CORRECAO.txt`.
- **Validação:** ZIP CRC OK, cabeçalhos PE `MZ` dos executáveis/DLL OK, hashes de todos os componentes originais idênticos aos do pacote completo anterior, nenhum `.sav` incluído. **Não houve QA de execução Windows neste chat** além das compilações e testes anteriores, portanto não dizer que botão de criar perfil foi exercitado em hardware real após reempacotamento.
- **Alterações no código do jogo, CLI ou launcher Python:** nenhuma. **Removido:** nada. Erro corrigido pelo empacotamento completo e diagnóstico no `.bat`.
- **Atenção a futuros agentes/distribuição:** NUNCA orientar usuário a baixar o artifact do **launcher isolado** como se fosse um pacote pronto para jogo. Publicar somente pacote FINAL DE QA que contenha os quatro componentes com hash, README de dependências e verificador. Se Windows Security colocar um componente em quarentena, não sugerir desligar antivírus; verificar detalhes e fonte assinada/legítima.
- **Rollback:** preservar pasta v0.7.2.1 e saves originais; extrair novo ZIP em pasta separada. Não copiar saves originais sem backup. **Ainda não implementado:** servidor dedicado, 4 jogadores, login online, backups automáticos em cada save, launcher Android equivalente.


## 16. MEGA atualização v0.8 / Pass 1 (decisões 101–116) — 2026-10-14

**User vote:** `101B 102B 103B 104B 105C 106C 107B 108B 109C 110C 111C 112A 113B 114C 115A 116A`. **NÃO interpretar como substituição das 100 escolhas antigas.** Arquivo exaustivo de decisões e plano de QA em [docs/LAN_V080_MEGA_DESKTOP_PASS1.md](docs/LAN_V080_MEGA_DESKTOP_PASS1.md).

**Branch:** `feature/lan-v080-mega-desktop-polish` sobre PR #8; [PR #9](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/9) draft. Último commit DEV deve ser lido do HEAD (muda após updates de docs). Baseline aprovado pelo usuário: `feature/lan-v0721-viewport-culling`, SHA `a87e2c49e453db32def5e71ba2a2e696a911d504`. **Não mesclar com base estável sem QA real.**

### Adicionado / modificado
- `tools/emerald_launcher.py`: sessão sem console CMD em modo normal com `CREATE_NO_WINDOW`, stdout verboso descartado e stderr limitado por execução em arquivo; CMD reaparece somente quando usuário ativa diagnóstico; lembrar último perfil e configurar IP/porta e diagnóstico num JSON externo ao save; minimizar launcher durante o jogo e reabrir ao encerrar, avisar erro e caminho de logs; impedir outro jogo simultâneo pelo mesmo launcher.
- Gerenciamento de backups: botões de criar backup e recuperar backup escolhido por número, somente com jogo fechado, via `emerald_profilectl.exe` existente (que controla lock e recusa saves estruturalmente inválidos); exigir confirmação antes de restaurar. **Não prometer verificação completa do checksum.**
- `src/platform/sdl2.c`: escala inicial inteira adaptada à área de trabalho, F11/Alt+Enter para alternar janela e fullscreen-desktop. Mantidos nearest neighbor, SDL integer scale e lógica SDL para Android inalterada.
- `scripts/verify_v080_profile_patch.py`: inversão somente dos trechos de vídeo **exatos e autorizados** antes da auditoria hash SDL antiga.
- `tests/test_emerald_launcher.py`: novos testes para persistência, configurações malformadas e proteção dos bytes do .sav.
- `docs/LAN_V080_MEGA_DESKTOP_PASS1.md`: decisões 101–116, implementação real, limites, QA e rollback.
- Workflows Windows/Android e launcher estendidos para executar na nova branch e no PR.

### Removido
- **Nada:** battle logic, NPCs, menus Emerald, maps, Pokedex, Quest UI, Fairy, physical/special, fast-forward, áudios, LAN SIO e formato do save continuam os antigos. Nenhum save pessoal foi aberto ou modificado.

### Testes e limitações
- Rastrear GitHub Actions: `build-v080-graphical-launcher.yml`, `build-lan-hybrid-windows.yml`, `build-lan-hybrid-android.yml`, `test-lan-v080-foundation.yml`, e regressões. Não declarar todos verdes até ler conclusões exatas e comparar SHA.
- Ainda sem teste do usuário da nova versão com escalonamento ou CMD, backup real, saída do jogo e retorno à interface.
- #106C: zona preta no frame vista no screenshot precisa ser investigada, sem inferir que fullscreen resolve corte interno.
- #109C: instalador completo Windows ainda pendente; #110C: filtros opcionais ainda pendentes; #111C: desenvolvimento paralelo por marcos, sem fingir que servidor existe; #112A: servidor dedicado terá controle no próprio launcher; #113B e #114C convites e atalho configurável futuros; #115A Windows primeiro; #116A 2/3/4 jogadores em etapas.
- **NÃO implementado:** SessionServer headless EHL8, lobby real, 4 participantes, autenticação opcional online, streamer de eventos multiplayer, Android GUI equivalente e backups automáticos a cada save manual.
- **Risco importante:** saída de `AgbMain`/flush ainda depende de revisão de ciclo de vida; backups manuais somente com jogo fechado; integração de saves tem validação estrutural sem checksum completo. **Teste em pasta nova e somente com cópias dos seus saves reais.**
- **Rollback:** usar jogo anterior aprovado v0.7.2.1 / branch `feature/lan-v0721-viewport-culling`. Não reescrever outro save durante teste.
- **Próximo passo:** validar compilação, testar GUI e viewport em Windows real, depois corrigir quaisquer bugs observados e iniciar estabilização de saves, M2 servidor dedicado.


## 17. QA concluído de compilação da MEGA Desktop Pass 1 (2026-10-14)

- **Branch/PR:** `feature/lan-v080-mega-desktop-polish`, [PR #9](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/9), ainda draft. A execução de referência ocorreu na revisão `d70fe058e0408c2c7147542dfbfb54c6ec10cb82` (mesmo código launcher e SDL do incremento; commits posteriores só acrescentaram documentação).
- **Launcher GUI Windows + unit tests Python + empacotamento PyInstaller:** [Actions 38522309384](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38522309384) **SUCCESS**, artifact `11874218835` contém `EmeraldLauncher.exe`. Testes incluem login local/último perfil e save invariável em laboratório.
- **Jogo Emerald completo Windows x86, LAN regressão, auditoria SDL legada com patch reverso:** [Actions 38522309182](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38522309182) **SUCCESS**, artifact `11874860082`. Executável contém literal `Fullscreen toggle failed`, parâmetros M1, e a DLL SDL2.
- **APK Android ARMv7 experimental:** [Actions 38522309156](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38522309156) **SUCCESS**. Isso só prova compilação do código compartilhado; o **launcher Android permanece o antigo** e não implementa a nova UI desktop.
- **Testes core LAN/profiles C99, sanitizers e Windows cross:** [Actions 38522309249](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38522309249) **SUCCESS**.
- **Artefato pronto para QA local** criado a partir dos dois builds acima e do CLI win32 existente da M1: `/mnt/data/Emerald_Hybrid_v0802_MEGA_Desktop_Windows_COMPLETO.zip`, **23.428.247 bytes**, **SHA256** `ce407080e021b2a3d3e48ce73de6c1d1e1ab1ac8c2ac0016c946a72508a58feb`. ZIP CRC testado, PE MZ verificados, arquivos com hashes internos: `EmeraldLauncher.exe`, `pokeemerald.exe`, `SDL2.dll`, `emerald_profilectl.exe`, `ABRIR_LAUNCHER.bat`, `PORTABLE_MODE.txt`, `LEIA_PRIMEIRO_MEGA_v0802.txt`, `SHA256_COMPONENTES.txt`. **Nenhum arquivo .sav incluído.**
- **CI ROM genérico** [Actions 38522309423](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38522309423): **FAILURE na etapa Compare**. Os builds nativos Windows/Android e testes M0/M1 acima são execuções separadas bem-sucedidas; **não declarar todos os checks CI green nem ignorar falha**. A causa exata do Compare não foi resolvida neste incremento.

**Modificado:** launcher GUI, SDL2 vídeo, testes e auditoria reverse-patch exata, workflows e handoff. **Removido do gameplay:** nada. **Não implementado ainda:** instalador, auto-backup pós-save, validação checksum completa, servidor headless, lobby, 3/4 jogadores, login online opcional, novo Android launcher, efeitos visuais opcionais, análise concluída da região preta do screenshot. **Não há gameplay QA de usuário deste ZIP ainda.**

**Rollback:** versão v0.7.2.1 testada em branch `feature/lan-v0721-viewport-culling`, SHA `a87e2c49e453db32def5e71ba2a2e696a911d504`; extração sempre em diretório separado, perfis locais não devem ser substituídos ou excluídos ao trocar de build.

**QA humana seguinte:** abrir launcher SEM CMD visível; perfil lembrado; zoom inteiro em monitor do usuário; F11/Alt+Enter; save/reopen; criar backup com jogo fechado e recuperar; encerrar, observar launcher retornar; conferir logs. Validar visual abaixo da tela com prints antes/depois. Depois abrir nova fase: safe save lifecycle, instalador e SessionServer com dois jogadores.


## 18. Distribuição corrigida: primeiro instalador Windows REAL (2026-10-14)

**Problema do usuário:** ao clicar em links anteriores do ChatGPT, não conseguia baixar/"instalar" a versão MEGA v0.8.2. Pacotes anteriores eram ZIPs portáteis, não instaladores, e o artefato GitHub do launcher isolado não continha o gerenciador de perfis.

**Solução aplicada:** branch `feature/lan-v080-mega-desktop-polish` / [PR #9](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/9) (DRAFT) agora contém:
- `packaging/emerald_hybrid_setup.nsi`: script de setup NSIS por usuário (`RequestExecutionLevel user`), cria shortcut do launcher no Menu Iniciar, desinstalador HKCU, instala sem `PORTABLE_MODE.txt`; **desinstalar preserva** `%LOCALAPPDATA%\\EmeraldHybrid\\profiles` e `logs`.
- `.github/workflows/package-v0802-complete.yml`: baixa binários já validados por GitHub CI, verifica tamanho/conteúdo e hashes SHA256 dos quatro arquivos do app (C++ jogo, Python launcher GUI compilado, SDL2, CLI), falha diante de ausentes ou saves incluídos; publica **um único artifact GitHub** com instalador e ZIP portátil completos.
- `docs/LAN_V0802_INSTALL_WINDOWS.md`: explicação dos dois métodos e passos em português.

**Build & QA:** [GitHub Actions RUN 38524395485 — SUCCESS](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38524395485), artifact ID **11875457719**, nome `BAIXAR_AQUI_Emerald_v0802_INSTALADOR_e_PORTATIL_COMPLETOS`. Download obtido e verificado no container do chat:
- ZIP externo `Emerald_Hybrid_v0802_INSTALADOR_e_PORTATIL_GITHUB.zip` — 44.604.935 bytes, CRC íntegro.
- `Emerald_Hybrid_v0802_INSTALADOR_Windows.exe` — 20.900.097 bytes, PE/MZ válido, SHA256 `0ef9e823932e0f3b3a0d25ae5e1a8a313aec538c109ca84b1c3f07eba11773f0`. Setup NSIS compilou no Windows CI. **Ainda não instalado/testado no PC do usuário.**
- `Emerald_Hybrid_v0802_PORTATIL_Windows.zip` — 23.743.567 bytes, CRC íntegro, contém `EmeraldLauncher.exe`, `pokeemerald.exe`, `SDL2.dll`, `emerald_profilectl.exe`, `ABRIR_LAUNCHER.bat`, `PORTABLE_MODE.txt` e instruções, **zero arquivos .sav**.
- O workflow teve 2 falhas iniciais CORRIGIDAS: (1) hash do CLI previamente usado não era o hash do artifact oficial — agora hash fixado `09a865bc08bed2d5d7673114db1f381a5a12ce2df260c89ae7e9bc0fe6d52679`; (2) NSIS resolvia caminhos relativos à subpasta `packaging/`; correção estrita `!cd ".."`. Apenas após ambas passou o run 38524395485.

**Alterado neste incremento:** distribuição/instalador/documentação. **Não alterado/removido:** código do game, sprites, saves, LAN, SDL2, cliente launcher, gameplay. As versões binárias embutidas são builds testados antes e hash-pinned; geração de instalador não prova funcionamento de gameplay no Windows final.

**Limitações:** binário NÃO assinado; Windows SmartScreen pode avisar e não deve ser desativado às cegas. GitHub Actions artifacts duram 30 dias e podem exigir login. Ainda falta QA usuário: instalar, criar/importar perfil, salvar/reabrir, desinstalar preservando save, CMD oculto e zoom. Conta online, servidor dedicado, lobby 4 jogadores, instalador Android e saves automáticos seguem pendentes.

**Rollback:** manter v0.7.2.1 aprovada em pasta separada; qualquer nova instalação não deve apagar/migrar perfis portáteis anteriores sem backup. Falhas de download do sandbox devem ser contornadas pelo link GitHub Actions acima, **não insistir apenas no mesmo sandbox**.

**Próxima IA:** abrir `docs/LAN_V0802_INSTALL_WINDOWS.md` e este registro; não afirmar instalação em PC do usuário já confirmada. Atualizar handoff a cada patch com IDs de run, SHA, falhas e pendências.


## 19. MEGA atualização — M2 servidor dedicado EHL8 com dois clientes de protocolo (2026-10-14)

**Confirmação do usuário:** o instalador Windows v0.8.2 gerado pela execução [38524395485](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38524395485) **funcionou no PC dele**. Isso confirma instalação/início, **não** QA completo de saves, multiplayer via servidor ou todos os modos.

**Autorização do usuário:** `funciuonou certinho, podemos partir para a mega atualização`. Decisões anteriores 1–116 continuam em vigor, sem necessidade de novo questionário geral. Prioridade: M2 servidor dedicado **real**, mas preservar jogo v0.8.2 e v0.7.2.1.

### Branch, arquivos e protocolo

- **Branch:** `feature/lan-v0803-dedicated-session-core`, derivada da `feature/lan-v080-mega-desktop-polish` no commit-base `3f94a665bc742d2130a856b5b153596def8445a4`. Após abrir PR, registrar seu número e SHA do HEAD real.
- **Adicionado:** `tools/emerald_session_server.py` (servidor asyncio dedicado, separado do jogo), `tests/test_emerald_session_server.py` (integração TCP local sem mocks), `.github/workflows/test-v0803-dedicated-server.yml` (testes Linux + Windows e build `EmeraldSessionServer.exe` Windows), `docs/LAN_V0803_DEDICATED_SESSION_CORE.md`.
- **Sem alterações em gameplay, saves, mapas, áudio, gráficos, UI, SIO, biblioteca C legada ou binário v0.8.2.** `AGENTS.md` e este `AI_README.md` atualizados. **Removido: nada**.
- **Funcionalidade do núcleo:** framing EHL8 conforme `src/lnet/lnet_session_v1.c` (28-byte header, 4KiB máximo), auth PIN local seis dígitos, identificadores de perfil com bloqueio de duplicidade na sessão, até **dois** slots de jogadores de protocolo, lobby ready/start, heartbeat, presença LANP validada, seq anti-replay, rate limit leve, logs sem PIN, desligamento após 15 min sem clientes.
- **Compatibilidade**: EHL8 **não pode** ser enviado ao mesmo raw SIO TCP de Cable Club/Presence; separar transporte e exigir ClientAdapter novo, mantendo P2P antigo como fallback. Por isso, apesar de agora existir um núcleo de servidor real, o botão **Hospedar servidor dedicado** do launcher **ainda deve ficar DESABILITADO para gameplay** até existirem cliente/game EHL e lobby operacional.
- **Saves:** NÃO há dados de save no servidor. No protocolo aparecem apenas profile IDs simples, sem Trainer ID, Pokémon, progresso nem credenciais. Não confundir unicidade local com conta autenticada.
- **Pin de 6 dígitos** é proteção simples para LAN privada, não serve para hospedar em WAN pública: sem TLS/criptografia/anti-cheat robusto.

### Testes / critérios de publicação

- Suíte local em loopback TCP foi exercitada em ambiente isolado de desenvolvimento, testando diferentes casos; **CI do repositório é a referência final** para Windows/Linux e existência do EXE. Registrar runs/conclusões reais; não declarar artefatos ainda não criados.
- Testes em `tests/test_emerald_session_server.py`: handshake, PIN incorreto/restrições por IP, entrar com 2, recusar duplicado/terceiro, sincronizar ready/start, retransmitir uma posição, rejeitar header magic/tamanho/versão errados e posição inválida.
- **Não testado ainda:** dois jogadores **dentro do Emerald** usando esse servidor, reconexão de 60s, lobby com interface, convite/trade, quatro jogadores, Android server, WAN, perfil/save e performance em hardware de 4GB. Não distribuir um pacote para jogar apontando para esse servidor antes do adapter do game.
- **Próxima etapa M2/2:** implementar SessionClient binário nativo C+SDL que faça handshake e integre PRESENCE ao game; depois M2/3 UI lobby no launcher e controle do servidor, 2 jogadores com save local; validar com hardware do usuário; depois 3/4.
- **Rollback:** `feature/lan-v080-mega-desktop-polish` é a versão com instalador validado pelo usuário; baseline LAN P2P jogável: `feature/lan-v0721-viewport-culling` commit `a87e2c49e453db32def5e71ba2a2e696a911d504`.

### M2/1 — Verificação final de CI

- **Build/QA confirmado** na revisão `f8c8aaec520c8033a549775cff12885bcd7fa7bd`: [Actions 38526266976](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38526266976), **SUCCESS** em duas plataformas. Ubuntu 24.04 + Windows GitHub Actions executaram testes `unittest` com sockets reais (6 testes: protocolo válido/inválido, PIN e cooldown, recusa de duplicado/terceiro, ready/start, relay de pose, desconexão), Python 3.12 e `py_compile`. O job Windows gerou `EmeraldSessionServer.exe` via PyInstaller.
- **Artefato Windows confirmado:** ID `11875946788`, `Emerald-v0803-EHL8-SessionServer-Windows-DEV-NOT-GAMEPLAY`, cerca de 9,5 MB. É ferramenta de desenvolvimento do núcleo de sessão; NÃO distribuir como launcher ou como jogo dedicado completo.
- **Primeira tentativa CI:** teste de recusa de conexão por PIN esperava só EOF; Linux reportou TCP `ECONNRESET`, que é comportamento normal para recusa de conexão que ainda tem bytes pendentes. Correção na suíte para aceitar EOF **ou** reset, mantendo a exigência de que o peer é rejeitado. Após alteração, jobs Linux/Windows passaram.
- **Diff revisado contra base:** `.github/workflows/test-v0803-dedicated-server.yml`, `tools/emerald_session_server.py`, `tests/test_emerald_session_server.py`, `docs/LAN_V0803_DEDICATED_SESSION_CORE.md`, `AI_README.md`, `AGENTS.md`. **Zero alterações em src/, dados, sprites, saves, Android ou jogo antigo.**
- **Estado:** [PR #10](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/10) permanece DRAFT. O CI pode ter outro check legado de ROM em execução ou falha independente; não declarar todo o conjunto de workflows verde sem verificar.
- **Teste funcional importante NÃO feito:** duas partidas reais do Emerald conectadas nesse servidor; ainda não existe adaptador de cliente EHL8 no jogo. Também permanecem pendentes slots reservados por 60s e autenticação forte para internet. 
- **Próximo trabalho:** M2/2 client adapter + testes host dedicado (um Windows servidor sem jogo e dois jogadores com saves separados), depois M2/3 integrar GUI lobby ao launcher; não reintroduzir confusão entre EHL8 e P2P Cable Club.

- **Artefato DEV conferido no contêiner do chat:** `Emerald_v0803_EHL8_SessionServer_WINDOWS_DEV.zip` (9.485.973 bytes), CRC OK, `EmeraldSessionServer.exe` (9.673.607 bytes) com PE `MZ` e SHA256 `00a45d6a474bafbad98d943dfae2f203a2e9e470bd2b9e5e39b0e4a82571f3d5`. Não é um instalador nem a versão de multiplayer jogável; não integrar ao pacote do jogador sem M2/2.


## 20. M2/2–M2/3 — Conexão EHL8 no próprio jogo e controle pelo launcher (2026-10-14)

**Pedido expresso do usuário:** continuar após M2/1, priorizando análise, polimento e testes antes de entregar. Todos os requisitos 1–116 seguem vinculantes. **Branch/PR:** `feature/lan-v0803-dedicated-session-core`, [PR #10](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/10), sobre v0.8.2 instalada com sucesso no Windows.

**Arquivos adicionados:**
- `src/lnet/lnet_session_client.h/.c`: cliente nativo C99 EHL8, TCP não bloqueante, frame 28B/4KiB, handshake AUTH PIN e JOIN com identidade de perfil, READY e START automáticos, heartbeat, validação e relay de LANP 18B, monotonic stale timeout de 3s, detecção de desconexão. Isolado do Cable Club e dos saves.
- `tests/native_ehl8_client.c` e `tests/test_ehl8_native_bridge.py`: compilam dois processos nativos C, conectam ambos no servidor Python EHL8 por TCP real em `127.0.0.1`, verificam movimentação remota nas duas direções e rejeição de protocolo inválido. Sem `.sav`, sem chamar AgbMain.
- `tools/emerald_session_server.py` agora aceita também `--pin-stdin` com segredo lido de pipe (legacy `--pin` para diagnóstico manual ainda funciona).

**Arquivos modificados:**
- `src/link.c`, `include/link.h`: entrada `PortLanRequestDedicatedClient`; reutilização EXATA da projeção do avatar remoto, suavização de movimento, culling e limpeza do sprite já aprovados pelo usuário em v0.7.2.1. Evita segunda implementação de sprite; não toca Quest UI.
- `src/platform/sdl2.c`: modo novo opt-in `--session-client=IPv4:PORT` com `--session-pin-stdin` (opção `--session-pin=...` manual alternativa), **exige perfil local válido e impede mistura com `--lan-host`/client raw SIO**. Sem essas flags funciona como v0.8.2; falhas de configuração retornam erro e não caem silenciosamente no save antigo. Buffer secreto temporário zerado após inicialização.
- `tools/emerald_launcher.py`: agora pode iniciar/parar **processo dedicado real** `EmeraldSessionServer.exe`, com PIN mascarado; checkbox para jogar usando EHL8 e mesma seção de IPv4/porta; P2P Cable Club antigo preservado como padrão. Launcher envia PIN por stdin tanto ao servidor quanto ao jogo e não persiste PIN em `launcher-settings.json`. O launcher gera logs locais e acompanha o game. Ainda **não** exibe lista de participantes, lobby de amigos com cards, QR nem convites.
- `scripts/verify_v080_profile_patch.py`: auditoria reversa ampliada **somente** para flags SDL autorizadas; baseline game antigo ainda é verificado.
- `tests/test_emerald_launcher.py`: validação de PIN seis dígitos, proibição de PIN em argv de game, modos novos.
- `.github/workflows/test-v0803-dedicated-server.yml`, Windows/Android workflows: executam prova C ↔ servidor Python e compilações full sem modificar o antigo P2P.
- `docs/LAN_V0803_DEDICATED_SESSION_CORE.md` expandido com protocolos, comandos, uso e riscos.
- **Removido do gameplay:** nada (sem mudanças de Hoenn, NPC, audio, sprites, Quest UI, batalha, save, Pokédex, turbo ou Fairy).

**Progresso verificado:**
- O teste `test_ehl8_native_bridge.py` de **dois clientes C** e servidor Python `EHL8` passou no GitHub Linux no [run 38528888486](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38528888486). Servidor Python em Windows/Linux passou unit socket QA da mesma revisão.
- Os builds nativos Windows/Android do **cliente C inicial** foram aprovados nas execuções [Windows 38528888473](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38528888473), [Android 38528888626](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38528888626). Essas execuções ocorreram ANTES do último refinamento de PIN via stdin e log; **verificar as execuções mais recentes no último código SHA para afirmar aprovação final.**
- Launcher PyInstaller Windows revisado aprovou no [run 38528894518](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38528894518), mas pré-PIN stdin. Nunca reutilizar build antigo com executável EHL novo sem conferir.
- **Não validado ainda:** duas janelas Emerald reais em Hoenn usando servidor dedicado, renderização em vídeo no hardware do usuário, saves com sessão EHL8 e evolução de mapa, reconexão 60s, Cable Club através do servidor, servidor Android ou 3/4 jogadores.

**Milestone respeitado:** #100A/#116A = primeiro **2 jogadores** com progresso independente; a integração real de gameplay precisa de QA humano antes de declarar aceite. **O servidor não transporta batalhas/trocas**; modos P2P legados continuam separados. Nenhuma conta online obrigatória (#81A). Servidor não contém saves nem autenticação robusta de internet. Proibir publicação em WAN pública; LAN/VPN confiável apenas.

**Instrução de teste seguro:** não sobrescrever v0.8.2 aprovada; instalar/extrair em pasta SEPARADA e criar/importar apenas **cópias** de .sav, garantir dois perfis distintos; iniciar servidor dedicado pelo novo launcher em um PC, entrar com ambos pelos launchers marcando EHL8 (ou via testes nativos), conferir chegada, mapa/camera/ocultação, encerrar e reabrir. Se falhar, enviar logs `cliente-ehl8.log` e `servidor-*.log` sem expor IPs privados.

**Rollback:** `feature/lan-v080-mega-desktop-polish` no commit `3f94a665bc742d2130a856b5b153596def8445a4` (instalador confirmado usuário) ou v0.7.2.1 `a87e2c49e453db32def5e71ba2a2e696a911d504` (LAN P2P aprovado). **Todos os saves fora da branch e intocados.** 

## 21. QA FINAL DO CANDIDATO M2 EHL8 Preview (14/10/2026)

**Status: código/testes e distribuições aprovados no CI, MAS jogabilidade real com dois Emeralds ainda aguarda QA do usuário.** Não classificar como lançamento estável.

### Compilações de mesma revisão de código
- `ddfdd5b536f49ef227c30bef08e7bbb720f3645b` é o código testado, após integração SDL2, client C, PIN por stdin e countdown no primeiro frame.
- ✅ **Servidor Python EHL8 e cliente C real / testes reais de dois processos e poses**: [GitHub Actions 38530326482](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38530326482) — Linux/Windows SUCCESS, inclui `EmeraldSessionServer.exe`.
- ✅ **Emerald jogo Windows x86 / auditoria histórica SDL2 / antigo LAN P2P**: [Actions 38530326166](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38530326166) — SUCCESS, binário `pokeemerald.exe`.
- ✅ **Emerald APK Android ARMv7 compatibilidade nativa**: [Actions 38530326361](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38530326361) — SUCCESS. **A nova interface dedicada Android NÃO foi implementada**; teste de compilação não equivale a teste com UI Android.
- ✅ **Launcher gráfico Windows PyInstaller e unit tests**: [Actions 38530326649](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38530326649) — SUCCESS.
- ✅ **Profile manager e framing C99/sanitizers**: [Actions 38530326395](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38530326395) — SUCCESS.
- ✅ Teste legado de LAN foi repetido após um evento isolado de timeout 25s e passou, preservando a base antiga sem desligar a auditoria. O CI genérico de ROM tem falhas históricas separadas: não declarar **todos os checks do repositório verdes** indiscriminadamente.

### Pacote distribuído com isolamento de saves
- `packaging/emerald_hybrid_m2_preview.nsi` — instalador **NSIS real, Windows sem admin**, instala em `%LOCALAPPDATA%\\Programs\\EmeraldHybridM2Preview`, sem sobrescrever v0.8.2. Lê `EHL8_PREVIEW_MODE.txt` para direcionar novos perfis e logs a `%LOCALAPPDATA%\\EmeraldHybridEHL8Preview\\profiles`; desinstalar **NÃO** apaga saves nem logs beta ou da instalação estável.
- `.github/workflows/package-v0803-ehl8-preview.yml` baixa **cinco binários SHA256-pinados** dos runs acima, valida hashes + tamanhos, recusa arquivos `.sav`, compila instalador NSIS + ZIP portátil em um único GitHub Actions artifact.
- ✅ [Actions 38530984109 — instalador e ZIP portátil](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38530984109) — SUCCESS, artifact ID **11877557469**, nome `BAIXAR_AQUI_Emerald_EHL8_M2_PREVIEW_INSTALADOR_e_PORTATIL`.
- Baixado e verificado no container deste chat: arquivo externo `Emerald_Hybrid_EHL8_M2_PREVIEW_GITHUB_COMPLETO.zip` (63.627.378 bytes, CRC OK), contém apenas os dois produtos esperados:
  - `Emerald_Hybrid_EHL8_M2_PREVIEW_INSTALADOR_Windows.exe`: 30.419.750 bytes, PE/MZ, SHA256 `674d8826e1701cc271672123029672fee97ef9c7eafbc4914b55759f894b38b4`.
  - `Emerald_Hybrid_EHL8_M2_PREVIEW_PORTATIL_Windows.zip`: 33.240.607 bytes, SHA256 `1edc83884f825d29693d6d39bb550a6c377e90671572df4b6fa68118e1df3082`, CRC interno OK, inclui `EmeraldLauncher.exe`, `pokeemerald.exe`, `SDL2.dll`, `emerald_profilectl.exe`, `EmeraldSessionServer.exe`, `ABRIR_LAUNCHER.bat`, `PORTABLE_MODE.txt`, leia-me/QA, **nenhum .sav**.
- Uma versão anterior do ZIP portátil tinha confundido o usuário porque baixou somente `EmeraldLauncher.exe`; neste pacote o download é **COMPLETO** e GitHub Actions é rota primária. O instalador é **não-assinado**; não recomendar desativar SmartScreen/AV.

### Resumo exato do incremento
- **Adicionado:** cliente nativo EHL8 `src/lnet/lnet_session_client.{c,h}`, testes C↔Python em sockets, `docs/LAN_V0803_M2_WINDOWS_QA_PTBR.md`, NSIS preview, workflow de pacote completo.
- **Alterado:** `src/link.c` reaproveita sprite/culling, `include/link.h`, `src/platform/sdl2.c` aceita modo dedicado com PIN lido via stdin, `tools/emerald_launcher.py` inicia/para servidor real e conecta ao dedicado, `tools/emerald_session_server.py` recebe PIN via pipe, auditoria SDL e testes do launcher, docs/AI handoff.
- **Removido:** nada do gameplay antigo, nenhuma quest, áudio, FX, batalha, história, mapa, sprite, mecânica ou save original. Os perfis da preview ficam **isolados**.
- **NÃO implementado:** batalhas/trocas através do novo servidor, proxy SIO entre pares, lobby gráfico completo com lista/ready/kick, 60s reserva de vaga/reconnect, 3/4 participantes, login online opcional, QR/discovery, Android launcher equivalente, criptografia de dados ou infraestrutura WAN. **Não abrir portas públicas.**
- **Ainda NÃO testado em runtime:** dois Emeralds em Windows exibindo personagens remotos, warp/camera, saves reais, desinstalação e SmartScreen no Windows físico do usuário. Critérios e roteiro em `docs/LAN_V0803_M2_WINDOWS_QA_PTBR.md`; exigir feedback antes de chamar M2/2 estável.
- **Rollback:** primeira opção `feature/lan-v080-mega-desktop-polish` (v0.8.2 instalador já confirmado pelo usuário); segunda opção `feature/lan-v0721-viewport-culling` SHA `a87e2c49e453db32def5e71ba2a2e696a911d504` para LAN P2P comprovada.
- **Próxima etapa:** instalar preview separada em 2 PCs, fazer QA com cópias de dois saves e comparar regressões. Só depois implementar lobby gráfico completo, recuperação, extensão para 4 e SIO de batalhas/trocas no dedicado.

**Nenhuma ação desta etapa acessou ou modificou os saves pessoais do usuário.**


## 22. M2 — reforço de QA da ponte C nativa e reconfirmação de contexto (2026-10-14)

**Pedido:** o usuário aprovou implementar/conectar EHL8 ao Emerald e solicitou análise, polimento e verificação antes de qualquer entrega. Ao retomar `feature/lan-v0803-dedicated-session-core`, a integração **já estava presente**, não recomeçar do zero: `src/lnet/lnet_session_client.c/.h`, `src/link.c`, `src/platform/sdl2.c`, GUI com controles dedicados e um workflow de pacote PREVIEW. GitHub HEAD deve ser consultado; PR #10 ainda draft.

**Verificação em commit pré-QA** `3757ecd0b2c6d38c1921b085575209ea205c6c0e`: builds Windows x86 e Android ARMv7, testes LAN, M0/M1 perfis, GUI, servidor EHL8 e pacote de preview **SUCCESS** no GitHub. Workflow `CI` genérico da ROM **FAILURE** separada, não chamar todos os checks verdes nem mesclar PR prematuramente.

**Adicionado nesta retomada (código de testes, sem gameplay modificado):**
- `tests/test_ehl8_native_bridge.py`: casos end-to-end reais com cliente nativo C contra servidor Python para (a) rejeitar PIN errado sem entrar no lobby; (b) negar conexão duplicada do mesmo profile ID sem substituir jogador existente.
- Testes anteriores de dois clientes C jogando poses em TCP localhost, handshake PIN/ready/start, falhas de framing e retransmissão permanecem ativos.

**QA novo:** [Actions 38533591020](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38533591020) foi executado sobre `2664c58a1089228c5276b27d4d0a67bd0bae5094`. Testes Linux de servidor e ponte nativa C/servidor Python **SUCCESS**; job Windows de servidor compila executable PyInstaller (verificar conclusão antes de declarar verde). Builds Android/Windows/native serão avaliados separadamente, nunca assumidos.

**Segurança e isolamento:** nenhum `.sav` foi carregado nos novos testes; todos os binários de teste são efêmeros; não houve alteração de mapas, batalha, SIO, áudio, sprites ou gameplay. O novo protocolo de sessão dedicado permanece separado do Cable Club P2P anterior. ID de perfil impede duplicação acidental de sessão, mas não é prova de identidade criptográfica em LAN.

**NÃO IMPLEMENTADO/NÃO VALIDADO:** QA em dois PCs reais com Emerald completo e saves independentes, reconexão com reserva de 60 segundos, robustez de trocas/duelos dedicados (ainda no P2P antigo), lobby gráfico com lista de conectados, Android servidor dedicado, quatro jogadores, proteção/backup automáticos pós-save. O preview **NÃO é release estável**.

**Recomendação e próximo passo:** preservar PR #10 experimental e solicitar QA do usuário no Windows com **3 máquinas lógicas** (servidor EHL8 + 2 clientes Emerald com perfis diferentes) antes de declarar jogabilidade dedicada validada. Se aprovar, implementar lista real de participantes/Ready UI e reconexão, depois até 4 players. README obrigatório em cada atualização.

**Rollback:** `feature/lan-v080-mega-desktop-polish` (instalador previamente confirmado pelo usuário), backup LAN validado `feature/lan-v0721-viewport-culling`. Nunca modificar arquivos de save originais.

## 23. Retomada: consertar late-join no EHL8 e mostrar jogadores reais no launcher (2026-10-14)

**Usuário pediu continuar a implementação e polir antes de entregar.** Recuperei HEAD do GitHub em vez de recomeçar. PR #10 (`feature/lan-v0803-dedicated-session-core`) já continha servidor EHL8, cliente C integrado no Emerald, launcher gráfico e instalador PREVIEW testados em CI. A v0.8.2 instalada pelo usuário e a v0.7.2.1 LAN aprovada continuam preservadas.

### Bug confirmado por leitura do código e resolvido

- **Entrada tardia** (#9A/#38A/#61A): o servidor deixava um novo jogador entrar quando `in_game=True` e enviava `START`, mas rejeitava o `READY=1` enviado automaticamente pelo cliente C após JOIN, resultando em desconexão. `tools/emerald_session_server.py` agora aceita o primeiro `READY=1` de um cliente no estado `GAME`; READY repetido é idempotente, **não** gera broadcasts redundantes. Outros payloads continuam inválidos.
- Novo teste TCP `test_running_room_ready_ack_does_not_disconnect`: duas pessoas entram e ficam prontas; uma sai; novo perfil ocupa slot aberto numa partida já iniciada; READY/HEARTBEAT continuam funcionando; seu POSE é retransmitido ao primeiro jogador. READY duplicado não gera `PLAYER_LIST` extra.
- **Sem afirmar reconexão pronta**: entrar no slot livre NÃO equivale a reservar a mesma vaga por 60 segundos com token autenticado. O requisito #60A/#86A continua pendente.

### Melhoria de qualidade do launcher

- Servidor emite eventos de contagem `EHL8_ROOM_COUNT=0/2`, `1/2`, `2/2` em mensagens INFO no log **sem IP, PIN ou ID de perfil**.
- `tools/emerald_launcher.py` usa `read_room_occupancy()` para ler no máximo os últimos 8192 bytes do log deste processo; status no painel apresenta **ocupação real** em vez de `até 2 jogadores`. Ausência de dados não é interpretada como zero confirmado.
- `tests/test_emerald_launcher.py` cobrem formato multilinha, log ausente, cauda grande e contagem inválida. O servidor real continua rodando separado do Emerald.
- **Não é lobby completo ainda**: lista de membros, ping, pronta/recusar, expulsar e convites com UI continuam pendentes.

### Registros de alteração obrigatórios

**Adicionado:** testes de entrada tardia + mensagens repetidas de READY + movimento pela sessão já iniciada; teste do parser de ocupação. **Modificado:** `tools/emerald_session_server.py`, `tools/emerald_launcher.py`, testes e `docs/LAN_V0803_DEDICATED_SESSION_CORE.md`. **Removido:** nada; nenhum arquivo `src/`, gameplay, mapa, Quest UI, sprites, arquivos .sav ou dados de usuário foi alterado nesta retomada.

**QA:** consultar a matriz do workflow EHL8 Linux/Windows, CLI/PIN, launcher Windows, construção do jogo Windows/Android e instalador de preview no commit mais recente. Não supor sucesso de runs anteriores como validação do HEAD atual. **Testes reais com duas janelas Emerald em Hoenn ainda não foram executados pelo usuário.** CI genérico de comparação ROM é separado do build PC/Android.

**Rollback:** `feature/lan-v080-mega-desktop-polish` (instalador v0.8.2 confirmado no PC pelo usuário), ou `feature/lan-v0721-viewport-culling` SHA `a87e2c49e453db32def5e71ba2a2e696a911d504` (LAN P2P testada). Não misturar perfis preview com saves originais; preservar `EmeraldHybridEHL8Preview` e `profiles/` ao atualizar uma preview.

**Próxima etapa:** verificar todos os workflows no mesmo SHA; enviar apenas build de preview quando íntegro, com roteiro QA e limitações; investigar integração de rendering em 2 PCs reais; depois implementar reserva de vaga por 60 segundos com identidade de sessão, painel lobby real e trade/battle SIO separado.

## 24. Gate de distribuição M2: artefatos testados no MESMO SHA (2026-10-14)

**Falha de processo detectada:** `.github/workflows/package-v0803-ehl8-preview.yml` buscava automaticamente componentes de runs antigos (`38530326166`, `38530326649`, `38530326482`, `38530326395`), sem garantir que o usuário recebesse correções recém-adicionadas. O ZIP poderia ser publicado como atualizado enquanto continha **executáveis antigos**, contrariando a política de QA da equipe.

**Corrigido:** o workflow agora aguarda as quatro compilações obrigatórias (jogo Windows, launcher gráfico, servidor dedicado EHL8 e núcleo de perfis) de **exatamente `GITHUB_SHA`**, consulta a API de Actions com permissão `actions:read`, exige conclusão `success` para cada uma, falha se alguma delas falhar ou não terminar, baixa os artefatos correspondentes e verifica assinatura PE MZ, tamanho mínimo e ausência de `.sav` em cada pacote. Emite `SHA256_COMPONENTES.txt` contendo `SOURCE_COMMIT` e hash real de cada um dos cinco binários (SDL2 incluída). Instalador NSIS e ZIP portátil incluem esse arquivo e continuam usando perfis beta isolados.

**Arquivos alterados/adicionados na retomada:**
- `tools/emerald_session_server.py`: READY tardio aceito exatamente quando o novo jogador entrou em jogo iniciado, idempotência sem flood; evento `EHL8_ROOM_COUNT` emitido apenas com ocupação, sem divulgar credenciais/IDs.
- `tests/test_emerald_session_server.py`: novo caso TCP da entrada tardia e pose do substituto após partida iniciada.
- `tools/emerald_launcher.py`: contador real lido do próprio log do servidor, limitado aos 8 KiB finais; logs ausentes deixam o estado como aguardo.
- `tests/test_emerald_launcher.py`: parser de eventos com multiline, logs ausentes, inválidos, tail grande.
- `.github/workflows/package-v0803-ehl8-preview.yml`: componentes do mesmo commit + manifest SHA256.
- `packaging/emerald_hybrid_m2_preview.nsi`: instala/remove `SHA256_COMPONENTES.txt` sem tocar nos saves do usuário.
- `docs/LAN_V0803_DEDICATED_SESSION_CORE.md`, `docs/LAN_V0803_M2_WINDOWS_QA_PTBR.md` e este `AI_README.md`: QA/rollback/continuidade.

**Removido:** nenhuma funcionalidade de gameplay, arquivo de save, mapa, mecânica, áudio, opção P2P ou Quest UI; nenhum `src/` foi modificado nesta retomada, apenas servidor, launcher, testes, empacotamento e documentação.

**QA de aprovação:** devem passar os mesmos testes Linux/Windows de socket e cliente C, builds Windows/Android, testes de launcher, regressão LAN e **o novo workflow de pacote sincronizado por SHA**. O workflow `CI` genérico de comparação ROM é uma etapa separada e historicamente falha; não afirmar `100% CI verde` se ela continuar vermelha. A conexão de dois processos completos `pokeemerald.exe` em máquinas físicas ainda requer teste pelo usuário com cópias de saves.

**Riscos/pêndencias:** reconexão com vaga por 60 segundos e token de retomada não implementada; lobby gráfico ainda sem nomes/ping/kick; troca/batalha EHL8 ainda sem proxy Cable Club, má qualidade de WAN pública (PIN não substitui criptografia), suporte a quatro participantes e a UI Android dedicados ausentes. Não promover PR #10 a release estável ainda. Testar novo pacote M2 em instalação separada da v0.8.2 previamente aprovada.

**Rollback:** `feature/lan-v080-mega-desktop-polish` é o instalador v0.8.2 confirmado pelo usuário; `feature/lan-v0721-viewport-culling` SHA `a87e2c49e453db32def5e71ba2a2e696a911d504` é a LAN P2P funcional. Preservar todos os perfis originais e nunca transportar `.sav` dentro do instalador.


## 22. Retomada do PR #10 — guarda do loop SDL2 + empacotamento por SHA (2026-10-14)

- **Origem verificada:** branch `feature/lan-v0803-dedicated-session-core`, HEAD antes da alteração `849929db684ca651abe8308878e3cba03837febb`, PR #10 draft. O novo SHA exato deve ser lido no HEAD/manifesto do pacote.
- **BLOQUEIO DETECTADO NA INSPEÇÃO DE CÓDIGO (não reproduzido visualmente):** em `src/platform/sdl2.c`, o `while (accumulator >= dt)` não tinha caminho de saída quando `isFrameAvailable` era falso. Se a thread AgbMain demorasse a produzir o quadro, o loop de interface poderia girar indefinidamente sem tratar eventos, inputs nem fechar. Adicionado `else { break; }`, mantendo o acumulador e a cadência já existente para a próxima iteração. Não altera as rotinas de vídeo pixel-perfect, Quest UI, fast-forward, áudio nem flash/save.
- **Alterados:** `src/platform/sdl2.c`; `scripts/verify_v080_profile_patch.py` (reverte somente o novo bloco ao auditar o hash do SDL antigo, continuando estrito para outras regiões); `AGENTS.md` (retira instrução obsoleta que dizia botão EHL8 desativado); `.github/workflows/build-lan-hybrid-windows.yml`, `build-v080-graphical-launcher.yml`, `test-lan-v080-foundation.yml`, `test-v0803-dedicated-server.yml` e `package-v0803-ehl8-preview.yml` (gatilhos push da branch e compilações de componentes mesmo após fix de jogo, por mesmo SHA); este `AI_README.md` e `docs/LAN_V0803_M2_WINDOWS_QA_PTBR.md`.
- **Adicionado:** `tests/test_sdl2_frame_pacing.py` (regressão estática de saída do loop + strip exato de auditoria). **Removido:** nenhum arquivo ou sistema.
- **Provas até o momento do commit:** leitura da fonte real e revisão dos workflows no GitHub. Teste novo é **ESTÁTICO**; os workflows precisam ser executados e inspecionados **no novo HEAD** antes de alegar compilação ou package. A compilação não é QA visual com dois Emeralds; CI anterior passou para o SHA 849929db, não automaticamente para o novo.
- **NÃO implementados:** reserva autenticada de 60s/reconexão automática (#60A/#86A), lobby visual remoto com lista/Ready e admin kick, PvP/troca no dedicado, host Android nativo e quatro jogadores. Falta principalmente testar dois clientes reais com saves/copias, sprite remoto, transição de mapas, fechamento, persistência e abertura de sessão em LAN em PCs reais. Sem teste de corrupção pós-crash, não prometer proteção absoluta.
- **Rollback:** SHA antigo `849929db684ca651abe8308878e3cba03837febb` para preview; branch `feature/lan-v080-mega-desktop-polish` em `3f94a665bc742d2130a856b5b153596def8445a4` preserva instalador v0.8.2 aprovado. Não tocar saves originais, testar em diretórios/perfis beta com backup recuperável.
- **Próxima IA:** conferir HEAD PR #10 e status por SHA das Actions, pacote instalador + ZIP portátil com `SOURCE_COMMIT`, validar games em dois PCs e resolver lobby + reconexão antes de sair de DRAFT. Todas as decisões 1–116 continuam válidas.


## 23. Hotfix do empacotamento NSIS — falha externa Chocolatey 503 (2026-10-14)

- **Origem:** commit `1851588dc4b5dc7c2bc2dfa20db62761dafca1e6`, PR #10 draft. No exato SHA, o workflow Windows x86, o launcher Windows, o EHL8 Python/C e os perfis M0/M1 passaram; a compilação Android ARMv7 também passou. O job de distribuição do workflow `package-v0803-ehl8-preview.yml` (run [38561477655](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38561477655)) **FALHOU** na instalação do NSIS: Chocolatey community feed retornou HTTP **503**. O ZIP portátil já tinha sido criado dentro do runner, mas o workflow falhou antes do upload, logo NÃO houve distribuição do pacote dessa revisão.
- **Correção em andamento nesta atualização:** substituir dependência única do Chocolatey por detecção de NSIS preinstalado ou download da distribuição **oficial NSIS 3.13 ZIP portátil** via HTTPS/SourceForge, com 3 tentativas, tamanho mínimo, extração, verificação de cabeçalho PE/MZ e fallback Chocolatey só quando necessário. Usar compilador existente sem instalar globalmente nem exigir UAC. O download do arquivo pelo HTTPS não equivale a verificação criptográfica por SHA256 contra valor previamente confiável; esta segurança adicional permanece possível aprimoramento.
- **Mudanças:** `.github/workflows/package-v0803-ehl8-preview.yml` (bootstrap resiliente), `build-v080-graphical-launcher.yml`, `test-v0803-dedicated-server.yml` e `test-lan-v080-foundation.yml` (gatilho para reconstruir os respectivos componentes no mesmo SHA até quando apenas workflow de distribuição muda), `AI_README.md` e o guia de QA. O workflow Windows x86 já executa em qualquer push não-Markdown. **Nenhuma fonte de gameplay nem nenhum save mudou. Nenhum arquivo removido.**
- **Testes:** informações confirmadas pelo log completo do GitHub Actions; novo workflow precisa concluir no SHA desta correção antes de afirmar que NSIS/instalador funcionou. Preservar `SOURCE_COMMIT` igual no manifesto de componentes, NSIS+ZIP e teste de que não há .sav no pacote. Os testes de socket e build não comprovam dois avatares em PCs reais.
- **Ainda NÃO implementado:** 60s reconnect/reserva autenticada, lobby visual com estado dos jogadores, batalha/troca dedicada, quatro clientes e teste visual/round-trip de dois saves. Todos os sistemas aprovados 1–116, SIO antigo, Quest UI, áudio e turbo preservados.
- **Rollback:** `1851588` para o patch SDL2 anterior; baseline v0.8.2 em `feature/lan-v080-mega-desktop-polish`. Após CI, testar a preview de forma isolada em 2 PCs com cópias de saves e reter PR em draft até QA humano.


### Correção da definição YAML do instalador (seguimento da seção 23)

- O primeiro patch do NSIS em `6bcd81abae6b8cbc7c335605f3a9f18602ee941f` gerou uma definição YAML inválida: a rotina de substituição de texto expandiu o trecho especial `$'` do JavaScript e duplicou o final do workflow. A Action [38562358203](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38562358203) falhou **antes de iniciar qualquer job**. Isso é erro na criação do workflow, NÃO no jogo.
- Corrigido reconstruindo a etapa por intervalos a partir do arquivo original íntegro do SHA 1851588, sem substituição de string com marcadores especiais. A validação estática confirmou apenas uma etapa de NSIS, uma de instalador, uma de upload, sem cauda duplicada. O workflow continua baixando NSIS 3.13 oficial em ZIP, conferindo executável MZ e usando Chocolatey somente como fallback.
- **Modificados:** `.github/workflows/package-v0803-ehl8-preview.yml` e `AI_README.md`. **Adicionados/removidos:** nenhum. **Ainda depende:** novo workflow rodar com sucesso no HEAD corrigido; dois jogadores reais, reconexão 60s e lobby completo continuam pendentes. Preservado rollback `1851588` e instalação estável v0.8.2.


### Segundo reparo da dependência NSIS (seguimento, 2026-10-14)

- O workflow sintaticamente válido `fb91998b710afd34ea2381fa401c4e2a5bad203f` gerou todos os binários Windows no SHA correto, mas a distribuição [run 38562722390](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38562722390) falhou novamente em instalar NSIS. O URL do SourceForge foi baixado como arquivo **menor que 1 MiB**, incompatível com ZIP oficial de 2,4 MiB (provável página de redirecionamento); depois Chocolatey retornou 503. Confirmado pelos logs reais. Nenhum instalador do SHA novo foi publicado.
- Adicionada uma terceira rota verificável: action `negrutiu/nsis-install` fixada pelo commit `f3339c88dba6fd08910d5275a943f8f746d94876`, distribuição NSIS fork via **GitHub releases**. A action é externa e não substitui auditoria de origem/cadeia de fornecimento; pode falhar sem interromper os outros fallbacks, porém a entrega só é liberada após presença de compilador PE, EXE instalador, ZIP, cinco executáveis, hashes e ausência de saves reais.
- **Modificado:** somente `.github/workflows/package-v0803-ehl8-preview.yml` e documentação `AI_README.md`. Nenhuma alteração de gameplay, formatos de save, EHL8, Cable Club, áudio ou imagens. Nenhum arquivo removido; nenhuma nova funcionalidade de jogo alegada.
- **Status de teste:** a nova Action ainda precisa ser executada no SHA que contém esta seção; aprovação anterior dos builds não certifica o novo pacote. QA real de dois jogadores e tarefas #60/#86 continuam pendentes.


## 24. M2 client heartbeat/liveness — correção após preview Windows gerada (2026-10-14)

- **Ponto de partida:** commit `77c8778b339e79cd633d35a995c845c2d0e9ab25` gerou com sucesso [instalador + ZIP portátil no run 38563401981](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38563401981), artefato `11893518458`. Os cinco componentes saíram do mesmo HEAD; isso não substitui QA humano dos dois jogadores.
- **BUG DETECTADO POR REVISÃO:** `src/lnet/lnet_session_client.c` colocava o HEARTBEAT atrás de uma condição `else if` que enviava POSE a cada ~100 ms. Quando o jogo estava em GAME, o fluxo de poses tornava a condição de heartbeat praticamente inalcançável, sobretudo quando o outro jogador estava ausente e não havia resposta de pose. Uma queda silenciosa de rede poderia ficar sem detecção explícita.
- **Correção:** agendar heartbeat EHL8 com prioridade a cada 10 s, mesmo enquanto são enviados snapshots; receber o eco do servidor e marcar falha após 25 s sem qualquer resposta durante PLAYING. O jogo continua local/offline quando a sessão falha e o avatar remoto some; sem novo SIO/alterações no Cable Club. O intervalo é configurável SOMENTE no build de testes via macro, a produção usa 10 s.
- **Teste adicionado:** `tests/test_ehl8_native_bridge.py` recebe teste de loopback real C↔Python com duas instâncias nativas recebendo poses e heartbeats, usando 250 ms de intervalo exclusivo ao teste. `tests/native_ehl8_client.c` ganha modo `linger` de aproximadamente 1,8 s para observar heartbeats sem deixar a suite demorar 10 s. Testes server antigos preservados. **Esse teste não inicializa Emerald/SDL2 nem manipula .sav.**
- **Modificado:** `src/lnet/lnet_session_client.c`, `tests/native_ehl8_client.c`, `tests/test_ehl8_native_bridge.py`, workflows de pacote/launcher/profile para acionarem rebuild por mesmo SHA, e este `AI_README.md`. **Adicionado/removido:** nenhum arquivo/feature removida.
- **Validação honesta:** esta atualização tem que passar CI EHL8 real, build Windows e Android, perfil e empacotamento novamente no HEAD. Teste de liveness foi escrito, não declarar verde antes de acompanhar Actions. **Ainda faltam** reconexão automática/reserva de slot de 60 s autenticada, lobby completo/Ready/admin, troca/batalha EHL8, UI Android dedicada e QA dos dois Emeralds Windows com saves pessoais em cópias. Reconhecer que marcar conexão como FAILED não equivale a reconectar automaticamente.
- **Rollback:** preview anterior `77c8778` (instalador e ZIP válidos no run 38563401981); v0.8.2 estável mantida em `feature/lan-v080-mega-desktop-polish`. Preservar todas as decisões 1–116 e não misturar pacotes entre commits.


## 25. Compatibilidade GBA agbcc: guards BIOS em MODERN=0 (2026-10-14)

- **Branch/HEAD de partida:** feature/lan-v0803-dedicated-session-core, commit c109a48e7c2bac6a4ee2093e882ece96ade4f46d; PR #10 draft. Run push 38564420979 PASSOU e gerou instalador+ZIP portátil, artefato 11893820682; todos os jobs de build Windows x86, launcher, perfil, EHL8 native e Android também PASSARAM para esse SHA. **Mas** o workflow legado de ROM CI, run PR 38564429341, FALHOU em Compare. Não declarar tudo verde.
- **Erro real do log:** agbcc (MODERN=0) tratou warnings como erros em src/AgbRfu_LinkManager.c:74 / CpuFill16, reclamando de declarações implícitas de _Static_assert, _Alignof e __builtin_choose_expr. A causa demonstrada é a condição "#if defined MODERN && !defined PORTABLE" em include/gba/syscall.h: **MODERN=0 ainda está definido** pelo Makefile (-DMODERN=0), ativando indevidamente as macros modernas de CpuSet e CpuFastSet.
- **Correção restrita:** modificar ambas as condições para "#if defined(MODERN) && MODERN && !defined(PORTABLE)", habilitando as verificações modernas somente quando MODERN=1, sem alterar o caminho PORTABLE nem o código dos jogos. Não remover testes de alinhamento dos builds modernos.
- **Adicionado:** tests/test_gba_syscall_guards.py (verificação da condição e compilação host C nos modos MODERN=0 gnu89, MODERN=1 gnu11 e MODERN=1+PORTABLE) e etapa leve anterior ao Compare no workflow .github/workflows/build.yml. **Modificados:** include/gba/syscall.h, workflow CI, AI_README.md e guia de QA. **Removidos:** nenhum.
- **Validação esperada:** confirmar novo workflow CI completo no novo commit. O teste host de header NÃO substitui a compilação agbcc ou um teste real de ROM; se o Compare revelar nova diferença ou restrição de base vanilla, registrar e investigar antes de suprimir. Verificar os demais workflows por mesmo SHA. A preview compilada c109a48 permanece válida como beta anterior; uma eventual correção de ROM não deve substituí-la silenciosamente.
- **NÃO implementado:** nova reconexão autenticada de 60 segundos, lobby completo, batalhas e trocas no servidor EHL8, quatro jogadores, QA presencial de dois jogos completos. Saves pessoais fora do CI e inalterados; preservar as 116 decisões e rollback de branch anterior.


## 26. Emerald v1.0 M1.1: laboratório de 2 jogos e 50 identidades (2026-10-16)

- **Nova branch isolada:** \`feature/emerald-v100-m11-50bots-lab\`, derivada de \`005de5e36bb189ccae49c08a2abe89fdd7f2297d\` (PR #10 draft). Não alterar nem mesclar a branch estável v0.8.2 automaticamente.
- **Nova fonte:** \`tools/emerald_qa_lab.py\` abre duas instâncias reais \`pokeemerald.exe\` com perfis \`QA_A\` e \`QA_B\` isolados por rodada. \`emerald_profilectl.exe\` importa apenas CÓPIAS ou cria flash vazia, mantendo todos os saves originais. Backup somente após as duas janelas encerrarem.
- **Novidade M1.1:** \`tools/emerald_qa_bots.py\` + botão \`SIMULAR 50 CONTAS\` simulam **25 pares** TCP EHL8 consecutivos (máximo 2 simultâneos), com HELLO/PIN/JOIN/READY/START, retransmissão LANP A↔B, LEAVE e reentrada na sessão. Bots não abrem game, não usam .sav, só conectam a \`127.0.0.1\`, PIN por stdin e relatório JSON.
- **QA:** \`tests/test_emerald_qa_lab.py\` e \`tests/test_emerald_qa_bots.py\` rodaram 13/13 testes disponíveis no pacote de fonte em Python 3.13 Linux; teste adicional de integração com \`tools/emerald_session_server.py\` de produção foi SKIP local porque o servidor não faz parte do pacote isolado. CI Windows deve executar esse teste com o repositório completo, compilar \`EmeraldQALab.exe\` e \`EmeraldQABots.exe\` e publicar ZIP complementar após validação.
- **Empacotamento:** workflow \`.github/workflows/build-v100-qa-lab.yml\`, \`LEIA_PRIMEIRO.md\` e BAT de build/lançamento inclusos. O pacote é **somente o laboratório**, exige \`pokeemerald.exe\`, \`SDL2.dll\`, \`emerald_profilectl.exe\` e \`EmeraldSessionServer.exe\` existentes lado a lado. Sem CMD no uso normal do launcher compilado.
- **Sem mudanças em:** jogo C/SDL2, servidor EHL8 original, rede P2P, sprites, Quest UI/PokéNav, save formats, instalação v0.8.2. Nenhum .sav incluído ou modificado.
- **PENDENTE:** QA do 2/2 no Windows real e saves após roundtrip; teste real do protocolo no CI Windows; LAN 2 PCs; reconexão protegida 60 segundos; convites/batalhas P2P↔EHL8; 4 jogadores, contas online e redesign definitivo launcher. Um print com sprites não substitui testes de duas instâncias de jogo.
- **Rollback:** PR #10 head \`005de5e\` e versão funcional \`feature/lan-v080-mega-desktop-polish\`. A branch M1.1 nunca substitui saves instalados.
- **Decisões 1–116 permanecem válidas;** a especificação separada v1.0 usa IDs \`V1-01\` a \`V1-72\`. Não confundir numerações.


## 27. Emerald v1.0 M1.2 — Continuar sozinho no mesmo save de QA (2026-10-16)

- Relato de gameplay: depois de abrir 2 jogos EHL8 com progresso separado, usuário não conseguia reabrir apenas um perfil de novo. A M1.1 sempre criava uma sessão nova de QA para 2 jogos.
- Solução: painel **CONTINUAR SOZINHO** no Laboratório; escolhe sessão QA persistida e QA_A ou QA_B, inicia somente uma instância offline com `--profile-root` e `--profile-id` da própria sessão. Nenhum novo save, pasta de sessão, servidor ou segundo jogo é criado na reabertura. Sessão pode ser encontrada depois de fechar e reabrir o laboratório; um perfil saudável ainda aparece se o save do outro estiver ausente.
- Segurança: verifica localização, marcador de QA, logs, symlinks/junctions e save de tamanho esperado; respeita bloqueio nativo de perfil. Backups são feitos somente depois de fechar a instância e apenas do perfil aberto. Relatórios novos `reopen-QA_...json` não sobrescrevem `report.json` existente. Não alterar saves reais do launcher, P2P, EHL8, sprites, ROM nem instalação estável.
- QA: testes locais do Lab 15/15 passaram e bots 4/4 passaram (1 teste de integração real SKIP no pacote sem servidor). Windows GitHub Actions é responsável por compilar `EmeraldQALab.exe` e validar integração no repo inteiro. QA com saves reais no Windows continua necessária para aprovação.
- Atenção: EHL8 exige 2 prontos para iniciar; a opção solo é offline, não reconexão protegida de 60 s. O jogo Windows recomendado é a preview com correção de paleta commit `8e519e0` do PR #10; a M1.2 distribui somente o Laboratório. Rollback do Lab para `704f48b7647b58bf628218d022ea0fb1ed4d0f33`.


## 28. M2.1-A — Monitor de lobby EHL8 (2026-10-16)

- M1.2 passou 4/4 testes com o usuário (abrir QA_A, QA_B, reiniciar Lab e multiplayer). Correção visual de paleta de avatar validada na PR #10.
- tools/emerald_qa_lobby.py cria janela LOBBY AO VIVO: monitora ocupação e estados reais apenas pelos logs de servidor e jogos locais da sessão, sem portas, PIN, saves ou processos de terceiros.
- ENCERRAR SALA termina somente o servidor gerenciado pelo Lab, com confirmação; duas instâncias e continuar sozinho permanecem funcionais. Ainda não suporta Pronto/Iniciar manuais, kick individual ou token de reconexão 60s: protocolo atual tem READY automático.
- Novo test_emerald_qa_lobby.py e CI Windows com hidden import explícito; QA visual obrigatória com 2/2, queda 1/2, encerrar servidor e reabertura offline de save.
- Entrega experimental PR #15, rollback para M1.2 commit 11f4742; preservar v0.8.2 estável e o pacote EHL8 com sprites corrigidos.


## 28. Emerald v1.0 M2.1-B — administração local real (2026-10-16)

- **Base aprovada pelo usuário:** M1.2 reabrir QA_A, reabrir QA_B, fechar/reabrir Laboratório e regressão multiplayer EHL8: **4/4 testes manuais OK**; sprites de May/Brendan na preview 8e519e0 também **6/6 OK**. Manter ambas versões de rollback.
- **M2.1-A:** monitor gráfico 'LOBBY AO VIVO' mostra estados de QA_A/B e ocupação real 0/2–2/2 pelos logs, e encerrar sala sem encerrar saves/jogos.
- **M2.1-B:** em `tools/emerald_session_server.py`, `--admin-stdin` opcional exige `--pin-stdin` e lê comandos privados `KICK QA_A`, `KICK QA_B`, `LOCK ON` e `LOCK OFF` de um pipe local, sem listener admin em rede. `JOIN` é recusado quando trancado; a remoção fecha somente o peer selecionado. O protocolo EHL8 dos clientes não muda, nem há leitura/escrita de saves.
- **Compatibilidade e rollback:** PyInstaller gera `EmeraldSessionServerM21.exe` novo e separado, preservando `EmeraldSessionServer.exe` da preview funcional. `EmeraldQALab.exe` prefere M21 somente se instalado; caso contrário, o monitor continua somente leitura e botões admin ficam desabilitados. `EmeraldQABots.exe` permanece no pacote, junto dos demais. Nada altera source de `pokeemerald.exe` nem formatos de save.
- **Testes:** `tests/test_emerald_session_admin.py` (TCP real/lock, kick nominal), testes laboratoriais de comando por pipe, regressão de estados, suíte server original, CI do Laboratório Windows para 3 executáveis. Validar run e artefato pelo **HEAD SHA exato** antes de distribuir.
- **QA humano necessário:** exibir 2/2, bloquear/liberar entradas, remover somente QA_B sem fechar QA_A, salvar/reabrir ambos offline, presença remota e simulador 50 contas. Não declarar v1.0 pronta até isso passar.
- **Não feito:** Ready/Start manual, autenticação de sessão 60 segundos, convites para PvP, transferência de saves, servidor público/internet, mais de 2 jogadores. Manter PR draft e histórico V1-01 a V1-72 e anterior 1–116.

## 28. M2.1-B aprovado e M2.2-A de reconexão EHL8 opt-in (2026-10-16)

- **QA humano aprovado:** o usuário confirmou que no Windows o lobby M2.1-B consegue bloquear e liberar novas entradas, e remover QA_B mantendo QA_A jogando. A regressão M1.2 (Continuar Sozinho e multiplayer) também havia sido aprovada 4/4. Manter esses resultados como baseline; a v1.0 ainda não está pronta.
- **Branch experimental nova:** `feature/emerald-v100-m22-reconnect-core`, derivada da versão M2.1-B (`2d0cb13255096c55fccadaa2aa6d138c86590108`), sem tocar na instalação ou perfis existentes.
- **M2.2-A servidor (não cliente do jogo):** `tools/emerald_session_server.py` agora suporta `--resume-v1` opcional. O padrão permanece DESLIGADO para manter compatibilidade com clientes Emerald anteriores. Protocolo EHL8 opcional com tipo 18, token aleatório `secrets.token_bytes(32)`, retenção da mesma vaga por até 60 s após queda em GAME, retomada autenticada via PIN+perfil+token, rotação do token, proteção contra replay/troca de identidade, expiração e revogação via KICK, sem dados persistentes ou novos ports de administração.
- **Não ativar --resume-v1 no jogo atual**: o cliente C nativo em `src/lnet/lnet_session_client.c` ainda não entende pacote 18 e não tenta reconectar. O próximo incremento M2.2-B deve atualizar e validar o cliente nativo e construir um jogo/servidor combinados, preservando a correção de paleta May/Brendan validada previamente.
- **QA automatizado:** novo `tests/test_ehl8_resume_v1.py` roda sockets reais localhost, tokens, reserva, entrada negada, lock, rotação, expiração simulada, revogação admin. Regressões `test_emerald_session_server.py`, `test_emerald_session_admin.py` também são executadas em Linux e Windows pelo `.github/workflows/test-v100-m22-reconnect.yml`. Windows empacota `EmeraldSessionServerM22.exe` e `EmeraldQAReconnect.exe`; o teste automático `--selftest` verifica o binário GUI empacotado antes do ZIP.
- **Teste para o usuário:** extrair o complemento M2.2-A numa pasta separada, abrir `EmeraldQAReconnect.exe`, clicar **EXECUTAR TESTES DE RECONEXÃO**, verificar 0 falhas/0 erros e enviar o JSON local caso falhe. Isso **não** testa a reconexão dentro de `pokeemerald.exe` e não lê nem modifica .sav.
- **Documentação:** `docs/V100_M22A_RECONNECT_QA_PTBR.md`. PR M2.1-B e branch estável mantidas; não mesclar automaticamente. LAN/VPN privada somente; PIN não é autenticação WAN.

## 29. M2.2-B — reconexão nativa do Emerald (2026-10-16)

- **Validação humana:** usuário abriu o kit M2.2-A no Windows e confirmou `Testes: 4 | falhas: 0 | erros: 0 | status: APROVADO`. Em M2.1-B já confirmou bloquear/liberar entradas e remover QA_B sem prejudicar QA_A. Não supor que o jogo Windows M2.2-B passou visualmente: esse último QA é pendente.
- **Branch isolada:** `feature/emerald-v100-m22b-native-reconnect`, PR draft #17, derivada de M2.2-A. Mantidos M2.1-B e v0.8.2 estável.
- **Cliente nativo:** `src/lnet/lnet_session_client.c/.h` guarda token EHL8 tipo 18 em RAM, tenta recuperar a mesma sessão e o mesmo perfil em até 60s, backoff de 0,5s/1,5s, limpeza do sprite remoto enquanto reconecta e invalidação definitiva ao receber KICK. Após autenticação, envia `RESUME = identidade + NUL + token de 32 bytes`. Após retorno do START, aguarda rotação do token. Nunca persiste token, PIN nem qualquer save. Sem pacote 18, o comportamento legado continua.
- **Correções críticas reveladas pelos testes nativos:** `src/lnet/lnet_session_v1.c` inicialmente rejeitava o novo tipo 18 tanto no encoder quanto no decoder; e na reconexão o novo `HELLO` usava indevidamente o session ID antigo, enquanto o servidor exige zero. Corrigidos, ambos os testes TCP com cliente nativo passam.
- **Servidor M22 opt-in:** `tools/emerald_session_server.py` recupera vaga com token aleatório/rotação conforme M2.2-A, mantém limite de 2. Novo comando **DROP QA_A/QA_B** só no stdin administrativo privado (e com `--resume-v1`) simula desconexão inesperada de um jogador para QA; KICK continua encerramento definitivo e não desencadeia reconexão.
- **Laboratório:** usa `EmeraldSessionServerM22.exe --resume-v1 --admin-stdin` somente em pacote M2.2-B com `EHL8_M22B_GAME_MATCHED.txt` e hashes SHA256 dos binários `pokeemerald.exe`/servidor verificados. O simulador de bots permanece no protocolo legado, sem token. Lobby apresenta **RECONECTANDO**, **VAGAS RESERVADAS** e botões **SIMULAR QUEDA QA_A/QA_B**. Saves seguem isolados.
- **QA:** `tests/test_ehl8_native_reconnect.py` inicia cliente C real e servidor Python real TCP, provoca queda de conexão, exige retomada e pose remota. `tests/test_ehl8_m22b_bundle_safety.py` testa hashes e fallback, `tests/test_lan_remote_palette_regression.py` retém correção May/Brendan. Workflow `.github/workflows/build-v100-m22b-native-windows.yml` exige testes nativos e de servidor/QA, compila jogo x86 e executáveis do Lab/servidor, publica ZIP PORTÁTIL com mesmo SHA. Revisar run final antes de divulgar.
- **Teste humano obrigatório:** `docs/V100_M22B_RECONNECT_WINDOWS_QA_PTBR.md` instrui instalar pacote isolado, testar 2/2, clicar SIMULAR QUEDA QA_B, observar 1/2 + reserva e volta 2/2, confirmar May/Brendan, KICK sem reconexão, saves reabertos individualmente e bots. **Sem promover a release estável sem esses testes.**

## 30. M2.2-B aprovada pelo usuário e M2.3 — START pelo anfitrião (2026-10-16)

- **QA real M2.2-B validado:** usuário confirmou 5/5 no Windows na build `5e53e40`: conexão 2/2, reconexão automática QA_B, reconexão automática QA_A, KICK administrativo sem retorno e integridade dos saves. Nenhum problema relatado. Valida esses casos, **não** estabilidade prolongada, queda superior a 60s, duas máquinas físicas ou P2P Cable Club.
- **Baseline preservada:** `feature/emerald-v100-m22b-native-reconnect`, PR draft #17, artefato aprovado. Novas alterações isoladas em `feature/emerald-v100-m23-host-start-lobby`, PR draft #18.
- **M2.3 escopo honesto:** servidor oferece `--host-start` **somente junto com** `--admin-stdin`; dois jogadores continuam enviando READY **automaticamente** pelo cliente C, mas o servidor espera o comando explícito de `START` por stdin do host. Antes do comando, 2/2 READY não inicia. START com menos de dois clientes, READY incompleto ou partida já iniciada é recusado.
- **Compatibilidade:** `manual_start=False` por padrão no servidor, mantendo o START automático aprovado no EHL8 antigo. O Laboratório só ativa `EmeraldSessionServerM23.exe --host-start --resume-v1 --admin-stdin` em ZIP com marcador `EHL8_M23_GAME_MATCHED.txt` cujos hashes SHA256 de jogo/servidor correspondem. As demais instalações permanecem com seus servidores anteriores.
- **Lobby:** campos PRONTOS, PARTIDA INICIADA, estados atuais, botão `INICIAR SALA (2/2 PRONTOS)` liberado somente quando 2/2 pronto e não iniciado. Mantém SIMULAR QUEDA QA_A/QA_B, KICK, LOCK e logs. Continuar Sozinho/saves/50 bots intactos.
- **Testes novos:** `tests/test_ehl8_m23_host_start.py` simula sockets TCP reais com 0/1/2 prontos, READY revogado, heartbeat enquanto espera, comando local START, manutenção do jogador restante. `tests/test_ehl8_m23_bundle_safety.py` verifica proteção por hash e leitura dos logs.
- **Build/QA:** `.github/workflows/build-v100-m23-host-start-windows.yml` compila executáveis game + servidor + Lab da mesma revisão, com marcadores de compatibilidade. `docs/V100_M23_HOST_START_QA_PTBR.md` exige testar espera por 30s, START manual, reconexão, sprites, saves e KICK no PC. **Nenhum QA real M2.3 concluído ainda; só o usuário pode confirmar.**
- **Próximo:** tornar Pronto/CANCELAR individual uma ação real de cada jogador (não apenas confirmação automática), e então os convites de batalha P2P conforme decisões V1-04C, V1-33A, V1-53A.

## 31. M2.3-A — abrir lobby/servidor ANTES dos jogos (2026-10-16)

- **Bug reportado com captura de tela:** em M2.3, o Lab só criava o servidor ao clicar `ABRIR 2 JOGOS (NOVO)`, abrindo as duas janelas simultaneamente. Abrir `LOBBY AO VIVO` antes exibia `SEM SESSÃO EHL8` / `SERVIDOR DESLIGADO`; `ENCERRAR SALA` dizia `Nenhum servidor local ativo`. Esse era um defeito do fluxo da UI, **não falha da reconexão M2.2-B**, que passou 5/5 testes humanos.
- **Branch isolada** `feature/emerald-v100-m23a-server-first-lab`, PR draft #19, derivada de M2.3, sem alterar os releases experimentais M2.2-B/M2.3 ou perfis reais.
- **Novo ciclo de vida:** `QASession.start_server_only()` prepara perfis de QA isolados por `emerald_profilectl import/new`, abre apenas `EmeraldSessionServerM23.exe` com PIN por pipe privado e devolve o controle da interface sem abrir `pokeemerald.exe`. O Lobby passa a refletir sala 0/2, pronto 0/2, START pendente. `ABRIR 2 JOGOS (NOVO)` depois chama `launch_games()` e vincula apenas os dois processos à **mesma** sessão, porta e PIN, sem iniciar servidor duplicado nem criar novos perfis. O PIN fica apenas em RAM.
- **Guardas:** rejeitar PIN/porta divergentes, duplicação de sessão ativa, tentativa de ingresso em servidor encerrado, e não criar backups/relatórios de jogo se nenhum jogo foi aberto. Botão de início manual do anfitrião permanece aguardando 2/2 READY reais; reconexão 60s, kick, travamento de sala, bots e Continuar Sozinho preservados.
- **Testes novos:** `tests/test_ehl8_m23a_server_first.py` cobre 0 jogos com servidor ativo, ingresso tardio dos 2 jogos, reutilização da sessão, proteção dos arquivos fonte, PIN/porta errados e backups somente após jogos encerrarem. `.github/workflows/test-v100-m23a-server-first.yml` valida testes no Windows/Linux (sucesso inicial); `.github/workflows/build-v100-m23a-server-first-windows.yml` gera ZIP portátil completo e verifica mesma revisão e SHA256 jogo/servidor.
- **Instruções exatas:** `docs/V100_M23A_SERVER_FIRST_QA_PTBR.md`. Testar no Windows: iniciar servidor sem jogo, abrir Lobby e verificar 0/2, depois abrir 2 jogos e verificar 2/2, aguardar 30s, clicar INICIAR SALA, testar SIMULAR QUEDA B/A, kick, sprites, saves e voltar para CONTINUAR SOZINHO.
- **Status:** correção implementada e QA de integração em andamento. **Não chamar QA humano aprovado antes do usuário reportar.** O pacote M2.2-B `5e53e40` continua sendo o baseline com 5/5 testes aprovados.


## 32. PASSAGEM DE BASTÃO PARA O PRÓXIMO CHAT — M2.3-A, build Windows VALIDADA no CI (2026-10-16)

### Origem da tarefa e solicitação expressa do usuário
O usuário enviou screenshot do Lab M2.3: ao abrir o LOBBY AO VIVO antes do jogo, a sala estava em SEM SESSÃO EHL8 / SERVIDOR DESLIGADO; o botão ENCERRAR SALA avisou Nenhum servidor local ativo. O usuário explicou: ABRIR 2 JOGOS sempre iniciava servidor e duas janelas simultaneamente, impedindo preparar o servidor antes. Depois pediu: "cadê? faz um log no arquivo que vc estava mexendo agr com tudo que for preciso para o proximo chat saber por onde começar ou continuar. junto, faça um prompt." Esta seção é a passagem de bastão explícita. NÃO recomeçar o desenvolvimento do zero.

### Branch, PR, commits e arquivo de continuação
- Repo: https://github.com/Fallzz16/pokeemerald-multiplatform
- Branch de desenvolvimento M2.3-A: feature/emerald-v100-m23a-server-first-lab
- PR draft #19: https://github.com/Fallzz16/pokeemerald-multiplatform/pull/19
- Base M2.3: feature/emerald-v100-m23-host-start-lobby, PR draft #18, base SHA 27f7d8ab081b3390bf03904a960c348d378bba3f.
- Último commit de **código** usado no ZIP Windows M2.3-A: a0fd2ac9f2eb8833c019728e4b44d8493cd47bd0. Há commits posteriores somente para documentação/handoff; sempre buscar HEAD atualizado antes de modificar arquivos.
- Código mais importante: tools/emerald_qa_lab.py. Outros arquivos: tools/emerald_qa_lobby.py, tools/emerald_session_server.py, src/lnet/lnet_session_client.c, tests/test_ehl8_m23a_server_first.py.
- Documento de aceitação: docs/V100_M23A_SERVER_FIRST_QA_PTBR.md. Consultar também AGENTS.md, capítulos anteriores deste AI_README e as decisões da v1.0 (72 escolhas, com batalhas P2P e saves independentes).

### M2.3-A implementada — fluxo correto da sala
1. Novo botão INICIAR SERVIDOR (SEM JOGO) junto das opções de porta e PIN, sem aumentar a altura da janela.
2. QASession.start_server_only(sources,port,pin) chama launch(...,server_only=True), usa emerald_profilectl para criar/importar apenas CÓPIAS isoladas de dois saves de QA, inicia UM servidor EHL8 em 127.0.0.1 e não abre pokeemerald.exe. Sessão do Lab e logs já existem e o LOBBY AO VIVO pode exibir 0/2 e READY 0/2.
3. Depois ABRIR 2 JOGOS (NOVO) detecta o mesmo servidor ativo sem jogos e chama launch_games(), criando somente os dois processos do jogo, reutilizando exatamente o mesmo diretório de sessão, porta/PIN e saves; não inicia servidor extra nem cria perfis novos.
4. O Lab rejeita PIN/porta diferentes, servidor encerrado e múltiplas sessões simultâneas. PIN apenas em RAM e pipe privado, não em argv/logs. Backups e report.json só após os jogos realmente iniciarem e terminarem; não backup prematuro ao criar só a sala.
5. M2.3 anterior permanece: READY é enviado automaticamente pelos jogos; o anfitrião controla START manualmente, depois de PRONTOS 2/2. Reconexão 60s, KICK, LOCK, SIMULAR QUEDA, emotes existentes, sprites e Continuar Sozinho não foram removidos.
6. A build M2.3 usa somente jogo e servidor da mesma edição com marcadores/verificação SHA-256. Não copiar executáveis isolados em outras versões.

### Estado de compilação verificado — IMPORTANTE, já existe o ZIP, não duplicar trabalho
- Workflow específico Emerald M2.3-A Server First Windows Preview: run 38869447665, SUCCESS em todos os jobs game, gui-tools, portable. https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38869447665
- Artefato PORTÁTIL COMPLETO aprovado do commit de código a0fd2ac9: ID 12032023830, nome BAIXAR_AQUI_Emerald_M23A_SERVIDOR_PRIMEIRO_COMPLETO_Windows. Download: https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38869447665/artifacts/12032023830
- Artefatos parciais (NÃO indicar para instalação combinada): game 12033235696; tools 12032745902.
- Workflow Emerald M2.3-A Server-First Lobby QA: run 38869447647, SUCCESS Windows e Linux. https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38869447647
- Workflow Emerald Hybrid v1.0 M1 QA Laboratory Windows: run 38869453864, SUCCESS.
- Workflow CI GBA legado: run 38869453799, FAILURE na etapa Compare. Não confundir com o build Windows bem-sucedido; investigar separadamente. NÃO afirmar que todos workflows do repo passaram.
- **A M2.3-A NÃO foi validada ainda jogando no PC do usuário.** Um teste com Popen mockado e CI não substitui teste humano. Não publicar v1.0 stable.

### Testes humanos confirmados antes desta entrega
- Paleta May/Brendan 8e519e0: 6/6 OK.
- Continuar Sozinho M1.2 11f4742: 4/4 OK.
- Lobby M2.1-B 2d0cb13: bloqueio/liberação e remoção individual OK.
- Protocolo M2.2-A: 4/4, falhas 0, erros 0, screenshot real de Windows.
- M2.2-B 5e53e40: **5/5 OK no Windows**, conexão 2/2, reconexão automática de QA_B, reconexão QA_A, kick que não reconecta e integridade dos saves, observações nenhuma. É o último baseline de gameplay integralmente validado nesses critérios; mantê-lo para rollback.
- M2.3 PR #18 e M2.3-A PR #19 ainda não receberam aprovação visual no Windows.

### Teste IMEDIATO que o próximo chat deve solicitar
Pedir que usuário extraia o ZIP completo M2.3-A em NOVA pasta, mantendo a M2.2-B intacta. Usar apenas cópias de saves ou criar QA novas. Abrir EmeraldQALab.exe:
1. Selecionar EHL8 local, configurar PIN/porta, clicar INICIAR SERVIDOR (SEM JOGO). Esperado: nenhuma janela pokeemerald.exe; LOBBY AO VIVO mostra SERVIDOR ATIVO, SALA 0/2, PRONTOS 0/2, PARTIDA INICIADA NÃO.
2. Clicar ABRIR 2 JOGOS (NOVO). Esperado: exatamente duas janelas, MESMO servidor, SALA 2/2, PRONTOS 2/2, PARTIDA INICIADA NÃO.
3. Esperar 30 segundos antes do START; ninguém cai/desconecta.
4. Clicar INICIAR SALA (2/2 PRONTOS); dois avatares se enxergam, andam e têm sprites May/Brendan corretos.
5. SIMULAR QUEDA QA_B e QA_A separadamente; cada um recupera sozinho em até 60 s, QA restante não congela.
6. REMOVER QA_B; B NÃO deve reconectar, A continua jogando.
7. Salvar e reabrir QA_A e QA_B por CONTINUAR SOZINHO; nenhum progresso ou save original é alterado.
Se falhar: pedir print do Lobby e logs servidor.log, QA_A-rede.log, QA_B-rede.log e report.json (sem PIN ou saves pessoais). Corrigir de modo reprodutível, recompilar pacote inteiro e atualizar este AI_README.

### O que falta no desenvolvimento v1.0
- Registrar QA real da M2.3-A; **não saltar esse gate**.
- M2.4: permitir Pronto/Cancelar real e INDIVIDUAL dos dois jogadores (hoje READY automático, START manual). Priorizar simplicidade e proteger protocolo.
- Depois: convites/aceite/recusa de batalhas P2P 1v1, retorno seguro ao overworld, UX launcher e QA com 2 PCs físicos. Não confundir EHL8 com Cable Club original.
- Regressões de saves, KICK, 60s, bots 50 identidades em 25 pares, paleta, desempenho, LAN; sem destruir M1.2.
- Installer/updater, multilíngue, backup/rollback e aprovação final do usuário são outros marcos; não declarar completos sem evidência.

### PROMPT SUGERIDO PARA O NOVO CHAT
"Continue o Pokémon Emerald Hybrid v1.0 do estado verificável M2.3-A, sem recomeçar nem perder sistemas ou saves. Leia AGENTS.md e AI_README.md (especialmente capítulo 32), no GitHub Fallzz16/pokeemerald-multiplatform, branch feature/emerald-v100-m23a-server-first-lab, PR #19. Confira HEAD e CI antes de editar. O novo botão INICIAR SERVIDOR (SEM JOGO) permite abrir lobby EHL8 0/2 antes de ABRIR 2 JOGOS, e depois usar START manual com 2/2 READY. Build Windows da revisão de código a0fd2ac9 passou: run 38869447665, artefato completo 12032023830; testes Windows/Linux passaram no run 38869447647. O CI genérico da ROM GBA ainda falha em Compare, separadamente. NÃO afirme QA humano M2.3-A aprovado: ainda aguardamos meu teste. M2.2-B 5e53e40 passou 5/5 testes humanos e é a versão de rollback. Primeiro me oriente a testar: servidor sozinho 0/2; ingresso de dois jogos 2/2; esperar 30s; START; quedas A/B; KICK; sprites; saves e Continuar Sozinho. Se eu relatar bug, corrija com testes automatizados e nova build completa, preservando o resto. Se passar, registre no AI_README e continue o roadmap com READY/CANCELAR individual, depois batalhas P2P 1v1. SEMPRE diga exatamente o que devo testar após cada entrega."


## 33. M2.3-B — ingresso individual no servidor já iniciado (2026-10-16)

**Relato do usuário:** print confirma servidor 0/2 ativo sem jogo; ao clicar REABRIR 1 CONTA aparece aviso Sessão ativa, enquanto ABRIR 2 JOGOS abre os dois. Causa verificada em `tools/emerald_qa_lab.py`: `reopen_solo()` é offline e bloqueia sessão, e `launch_games()` abria exatamente dois processos. Não é evidência de falha do EHL8 nem dos saves.

**Alteração direcionada:** adicionados botões ENTRAR QA_A / ENTRAR QA_B para aproveitar sessão EHL8 previamente iniciada; `launch_single()` usa perfil existente, porta/PIN preservados e recusa duplicação. ABRIR 2 JOGOS passa a preencher apenas perfis ainda não lançados. Perfis registrados separadamente para backups/relatórios e guarda no monitor para não finalizar uma sala só porque o primeiro jogo individual foi fechado antes do ingresso do segundo. `CONTINUAR SOZINHO` mantém semântica offline. Nenhum código do jogo, servidor, save original, SIO, sprites, Cable Club ou gameplay foi alterado.

**Arquivos:** `tools/emerald_qa_lab.py`, `tests/test_ehl8_m23a_server_first.py`, `docs/V100_M23A_SERVER_FIRST_QA_PTBR.md`, `AI_README.md`. **Build e QA Windows M2.3-B ainda pendentes nesta etapa:** não usar artefato antigo da M2.3-A para alegar presença dos botões novos. Aguardar workflow do novo SHA, conferir pacote integral com hashes, e QA real do usuário. **Rollback:** M2.2-B `5e53e40` com 5/5 testes reais; M2.3-A `a0fd2ac9` para fluxo 0/2 + entrada simultânea. **Testes manuais:** iniciar sala 0/2; ENTRAR QA_A => 1/2; ENTRAR QA_B => 2/2; esperar 30s; START; reconexão B/A, kick, sprites e saves; segundo cenário B primeiro e ABRIR 2 JOGOS acrescentando apenas A. Sem tocar saves originais.


## 34. M2.3-B2 — correção do ciclo de vida do Lab (2026-10-16)

Relato real e três capturas: entrada individual abre pokeemerald.exe (esperado para cliente EHL8), mas depois de fechar QA_A não era possível entrar novamente, e uma sala encerrada ainda deixava porta ocupada. Causas no código: `game_profiles` bloqueava relançar slot com processo encerrado; monitor finalizava sala quando ambos processos morreram; stop() terminava servidor sem esperar saída. Corrigido relançamento de slot somente quando seu processo anterior encerrou, preservando caminho de save isolado, sem duplicar registro de backup. O monitor só completa quando servidor e jogos acabaram. stop() aguarda processos filhos e só força o próprio filho após timeout. Novos testes regressivos de reentrada. Não confundir cliente de jogo com futura UI de Pronto/Cancelar independente, ainda não implementada. Nenhum código de ROM, EHL8 servidor, sprites ou SAV original alterado. QA Windows da correção e compilação completa ainda a verificar. Rollback M2.2-B 5e53e40. Teste: iniciar sala 0/2, QA_A 1/2, fechar A e reabrir A na mesma sala, QA_B 2/2, aguardar 30s, START, saves; parar testes e iniciar outro servidor na mesma porta.


## 35. Auto QA consolidado — regressão automatizada e jogadores simulados (2026-10-16)

**Pedido:** testar funcionalidades de diversas maneiras simulando jogadores, de forma repetível e sem tocar nos saves pessoais. Implementado o orquestrador `tools/emerald_auto_qa.py`, que reúne suites existentes de protocolo EHL8, servidor de produção via sockets, bots com pares/identidades efêmeras, reconexão, pin/admin, M2.3-A/B/B2 Lab, locks, baseline e regressões de segurança. Execução: `python tools/emerald_auto_qa.py --group all --repeats 1 --report auto-qa-report.json`; intensidade adicional `--repeats 5`; `--group lab|protocol|safety`. Limite de 20 repetições, timeout individual de 5-600 s, sem shell, lista de testes explícita e relatório JSON com PASS/FAIL/TIMEOUT e saída curta. Falhas causam código de saída não zero. O workflow `.github/workflows/test-v100-m23a-server-first.yml` foi alterado para executar Auto QA no Windows/Linux e publicar relatório mesmo se testes anteriores falharem.

**Limitações transparentes:** a simulação já existente de 50 identidades ocorre em 25 pares de dois (NÃO 50 simultâneos); o Auto QA ainda NÃO aciona teclado/GUI real no `pokeemerald.exe`, NÃO observa pixels/sprites nem testa gameplay real de batalhas ou leitura e persistência de .sav dentro do jogo. Ações reproduzidas são no nível de rede, processos mockados e testes de integração do servidor. CI é condição necessária mas insuficiente para chamar v1.0 jogável. Build Windows nova e QA humano devem ser confirmados por SHA. Nenhum código de jogo/servidor ou save foi modificado nesta implementação; rollback último M2.2-B aprovado `5e53e40`.


## 36. Automação independente do CI GBA legado (2026-10-16)

**Solicitação:** acelerar o projeto automatizando toda a regressão que for viável. Inspeção do CI no commit 9c19cf60: run 38985643638, job 117256362623, falha **GBA Compare** devido ao compilador antigo (`varasm.c:3013: Internal compiler error`, avisos `_Alignof`/`__builtin_choose_expr`). Isso NÃO valida nem invalida o Auto QA Windows. M1 QA Windows run 38985643623 passou. Não misturar critérios de qualidade de plataformas.

**Adicionado:** workflow independente `.github/workflows/emerald-auto-qa.yml` com eventos push na branch e execução manual com 1/3/5 repetições; matriz Windows/Ubuntu, compilação Python, runner `tools/emerald_auto_qa.py`, resumo por suíte no GitHub Actions e download de relatórios JSON por plataforma mesmo quando falham. Não executa ROM GBA Compare. CI separado continua intacto, sem desabilitar verificações. O workflow anterior de QA específico permanece para regressão. Nenhum .sav, código do jogo/servidor ou protocolo foi alterado nesta etapa.

**Status:** workflow foi commitado, mas jobs ainda precisam ser verificados em seu SHA; não anunciar Auto QA aprovado, nem build Windows completa, sem execução verde. Interface com controle real de NPCs, movimentos em Hoenn, batalha e save visual permanece fora deste executor; QA humano segue necessário. **Rollback:** M2.2-B `5e53e40` aprovada em 5/5.

**Próximo:** verificar resultados Windows/Linux e seus artefatos, corrigir suites quebradas com causa reproduzível e abrir novos cenários; só depois integrar UI Auto QA ao Lab e uma camada opcional de automação de input do jogo isolado.


## 37. Escopo de distribuição confirmado pelo usuário — PC e Android (2026-10-16)

O usuário esclareceu expressamente: NÃO é necessário entregar ROM GBA; pretende jogar somente no PC via aplicativo/EXE e no celular via aplicativo/APK. Portanto, priorizar builds, regressões, compatibilidade e lançamento Windows + Android; crossplay EHL8 entre dispositivos é objetivo sujeito a implementação e QA reais. A falha do workflow GBA legado na etapa Compare NÃO bloqueia a aceitação das plataformas-alvo e deve ser reportada separadamente, nunca ocultada. Não excluir nem adulterar pipeline legado como reação automática; apenas removê-lo dos gates de lançamento Windows/Android. Não confundir ausência de obrigação de distribuir ROM GBA com autorização para alterar ou apagar assets e código compartilhados. Auto QA deve evoluir para cobrir builds Windows/Android, clientes e saves isolados; não declarar Android ou crossplay aprovados até haver evidência. Nenhum save ou código alterado nesta nota.


## 38. Estabilização v1.0 — correção de reentrada e Auto QA multiplataforma (2026-10-16)

**Pedido:** mega atualização para obter preview jogável/testável, sem perder as versões e saves aprovados. **Entregue nesta iteração:** em `tools/emerald_qa_lab.py`, corrigido fluxo `launch()` para reabrir um ou ambos clientes que já encerraram enquanto o servidor EHL8 da sala continua ativo (antes bloqueava após histórico de dois perfis). Novo teste `test_open_two_again_after_both_windows_closed_same_server` garante não recriar servidor, não duplicar processos/saves nem encerrar a sala antes da hora. `tools/emerald_auto_qa.py` agora marca claramente SKIP dos fixtures C POSIX na matriz Windows (Linux executa os testes nativos), sem transformar skips em PASS nem em falhas; `tests/test_emerald_auto_qa_runner.py` protege limites, comportamento de SKIP e contagem correta de falhas. O Auto QA foi ampliado para executar seus próprios testes em `safety`.

**Não mudou:** código do jogo, servidor, protocolo EHL8, batalhas, sprites, dados originais de save, ROM GBA legada, Android e APK. **Não implementado:** UI de Pronto/Cancelar individual, batalhas P2P por convite, automação gráfica real, crossplay validado ou APK estável. **Build Windows completa e CI deste HEAD:** verificar execuções e SHA exato antes de indicar artefato; não chamar preview de release ou M2.3 aprovado por teste humano até obter QA. O CI Compare da ROM GBA é legado e não gate das entregas desktop/APK. **Rollback:** M2.2-B `5e53e40`, 5/5 testes do usuário aprovados. M2.3-A `a0fd2ac9` apenas para referência do fluxo anterior.

**QA manual obrigatório após build verde:** servidor 0/2 sem jogo; QA_A entra 1/2; fechar QA_A; reentrar QA_A; QA_B 2/2; aguardar 30 segundos sem START; START anfitrião; movimento/sprites; simular queda de A e B; KICK; save e Continuar Sozinho. Novo teste: fechar ambos os jogos, manter servidor, clicar ABRIR 2 JOGOS novamente e conferir 2/2 sem criar outro servidor/perfis. Depois PARAR TESTES e reutilizar mesma porta em sala NOVA. Se falhar, anexar `servidor.log`, `QA_A-rede.log`, `QA_B-rede.log`, `report.json` sem PIN/saves pessoais.


### Complemento do incremento 38 — gate de empacotamento Windows

O workflow `.github/workflows/build-v100-m23a-server-first-windows.yml` foi reforçado: antes do PyInstaller do Lab, o job `gui-tools` executa `tools/emerald_auto_qa.py --group lab` e `--group safety`, falha se houver regressão e publica `M23A-qa-evidence` com relatórios JSON mesmo quando os testes não passam. Os executáveis Windows e o ZIP completo só podem seguir pela cadeia `game` + `gui-tools` -> `portable` se seus jobs terminarem com sucesso. Isso é uma proteção de build, NÃO teste de gameplay. O CI GBA Compare continua separado. A revisão final do workflow não havia sido aprovada pelo GitHub Actions na hora da documentação; conferir HEAD, jobs e artefatos antes da distribuição. Nenhum save foi utilizado ou alterado.


## 39. Hardening da mega atualização: rollback de lançamento parcial (2026-10-16)

**Diagnóstico:** no Lab `QASession._spawn_games`, o processo recém-criado era adicionado à lista ativa antes de completar o envio do PIN. Se o pipe falhasse, podia sobrar um filho em execução e/ou slot marcado como iniciado. Em `launch_games` um erro no segundo jogo podia deixar o primeiro recém-criado vivo com sala parcialmente preparada. **Correção:** só registrar processo após confirmação do envio de PIN; falha encerra apenas filho criado pelo Lab, e `launch_games` desfaz lançamentos novos dessa operação, preservando instâncias anteriores já ativas e o próprio servidor. Adicionado teste `test_failed_second_game_rolls_back_only_new_children` com BrokenPipeError simulado. Sem alterar save, ROM, servidor ou fluxo offline. **CI e gameplay real da revisão:** ainda exigem conferência; não afirmar QA aprovado. Rollback seguro: M2.2-B `5e53e40`.


## 40. M2.3-B2 preview Windows — pacote rastreável para teste (2026-10-16)

**Solicitação:** preparar toda atualização necessária à próxima validação, sempre com link EXATO. O workflow existente `.github/workflows/build-v100-m23a-server-first-windows.yml` disparado por push e manual mantém jobs `game`, `gui-tools`, `portable`, verificações binárias PE, SHA256 do jogo e dos servidores, proibição de arquivos `.sav` no pacote, Auto QA Lab e Safety como gate. Corrigido o nome confuso de distribuição: agora o nome de exibição da execução é `Emerald M2.3-B2 Windows Complete Preview`, e o artefato ZIP é `BAIXAR_AQUI_Emerald_M23B2_PREVIEW_COMPLETO_Windows` com arquivo `Emerald_Hybrid_M23B2_PREVIEW_COMPLETO_Windows.zip`. O pacote inclui `REVISAO_EXATA.txt` com SOURCE_COMMIT do build e `TESTAR_ESTA_BUILD.md` com checklist de QA. Documentação `docs/V100_M23A_SERVER_FIRST_QA_PTBR.md` ampliada para reentrada individual, relançamento dos dois clientes, 30 segundos sem autostart, queda/reconexão, KICK, encerrar e reaproveitar 45680, sprites e saves. **Cuidado:** mudança do nome não é declaração de testes aprovados; workflow/artefato da exata revisão só devem ser oferecidos se comprovados por consulta à execução e ao artifact ID, nunca inventados. GitHub API conectada mostrou M1 QA Windows em verde no commit anterior `e25fa8ee`, e CI GBA Compare legado vermelho; não equivale a aprovação de build M2.3-B2. Não houve alteração de assets, servidor, gameplay ou saves nesta etapa.

**Link de workflow (não link de artefato):** https://github.com/Fallzz16/pokeemerald-multiplatform/actions/workflows/build-v100-m23a-server-first-windows.yml
**Gate seguinte:** identificar run de sucesso com os três jobs, hash mesmo SOURCE_COMMIT, obter ID exato do ZIP, enviar URL do artifact, executar QA humano. Baseline rollback continua M2.2-B `5e53e40`.


## 41. Verificação destrutivamente isolada do ZIP final — M2.3-B2 (2026-10-16)

No workflow de build Windows `.github/workflows/build-v100-m23a-server-first-windows.yml`, o job `portable` ganhou etapa posterior à compressão que **extrai o ZIP produzido para diretório temporário de verificação** (`verify-portable`) e valida: existência do ZIP, `REVISAO_EXATA.txt` com `GITHUB_SHA` exato, marcador da mesma revisão em `SHA256_COMPONENTES.txt`, presença de executáveis/SDL2/bat/roteiro, SHA256 de cada arquivo listado no manifesto e proibição de `.sav` no ZIP extraído. Qualquer divergência falha o job e impede publicação de artefato final pelo próximo passo. Não usa nem altera perfis do usuário. O arquivo compactado é o mesmo enviado como artefato, sem troca de componentes. **Status:** script commitado, CI do pacote e QA humano ainda precisam ser confirmados; não há download novo verificado nesta etapa. CI M1 da revisão anterior estava verde; GBA Compare legado falha separadamente. Rollback M2.2-B `5e53e40`.


## 42. Entrega contínua: link EXATO do artefato Windows no próprio GitHub Actions (2026-10-16)

O usuário pediu continuar sem interrupções e sempre fornecer link exato, sem passar páginas genéricas como se fossem o download. O workflow `.github/workflows/build-v100-m23a-server-first-windows.yml` agora dá identificador `upload_portable` ao upload final e, somente após sucesso, insere no `GITHUB_STEP_SUMMARY` do job portable a URL **real** retornada pelo `actions/upload-artifact@v4` via `steps.upload_portable.outputs.artifact-url`, o ID real do artefato e o `GITHUB_SHA`. Se o upload não fornecer URL/ID, o resumo falha; nenhuma URL é inventada. A etapa é posterior às verificações de ZIP, hashes e save. Arquivos anteriores/saves/intensidade dos testes inalterados. Ainda deve-se confirmar execução real deste HEAD e obtenção do artefato; o workflow automático por push pode não estar acessível via conector GitHub que expõe apenas runs do PR, portanto falta de listagem não implica ausência de execução. O usuário quer entrega completa, não pequenos relatos. Base rollback M2.2-B 5e53e40. Commit da correção no resumo de link: 98d41de0acef9cc25532c5fe4ff240271941f0fb.


## 43. M3.0 Playable Evolution — decisões 1–24 e sequência vinculante (2026-10-16)

**Escolhas usuário:** Rodada 1: `1D 2D 3D 4D 5C 6D 7D 8D`. Rodada 2: `9D 10D 11A 12C 13D 14D 15C 16D 17D 18D 19D 20D 21D 22D 23D 24D`. **Importante 11A: personalização visual do protagonista ficará somente em Brendan e May; NÃO incluir roupas/cabelos/cosméticos**. Preferência confirmada de evitar repetidas perguntas/entregas fragmentadas; trabalhar autonomamente até obter pacote testável e fornecer link exato.

**Especificação adicionada:** `docs/V100_M30_PLAYABLE_EVOLUTION_ROADMAP_PTBR.md` contém interpretação fiel de cada decisão, marcos M3.0-A a M3.0-F, dependências explícitas, critérios de aceite, riscos e separação de build Windows/Android e QA de protocolo versus gameplay real. Ordem: estabilizar ZIP e gameplay Windows M2.3-B2/M3-A; lobby READY/CANCELAR e amigos; batalhas 1v1 e trocas seguras e coop; UX/desempenho; APK/crossplay; QA completo de beta. **Ainda NÃO implementados** novos recursos de gameplay M3.0, nova APK ou crossplay; esta etapa é planejamento, sem alteração de saves/código executável. Baseline rollback `5e53e40` M2.2-B, QA humano 5/5. Branch `feature/emerald-v100-m23a-server-first-lab`, PR #19, commit da especificação `316b0e9b64687b53d6c10e6998f15461e15fdd0b`. Compilação/QA da especificação: não aplicável (documentação somente); QA prévio do pacote ainda pendente.


## 44. M3.0-A — teste de reuso real da porta TCP (2026-10-16)

O usuário solicitou continuar desenvolvimento sem perguntas de confirmação. Adicionado `tests/test_ehl8_m30_port_lifecycle.py`: inicia o servidor EHL8 **real** de `tools/emerald_session_server.py` como subprocesso local isolado por três rodadas, alimenta PIN via stdin (nunca argv), verifica escuta TCP em 127.0.0.1, encerra o filho e tenta bind imediato da mesma porta. Não instancia jogo nem toca saves. Regressão ligada à suíte protocol em `tools/emerald_auto_qa.py` (commit `87c82c4f018d41591e5622d1bfe36b4ae19543e6`), com o teste criado no commit `e348814f521f420c86182e39b8cb12443e4a8fcf`. Teste não equivale a QA do exe Windows, sprites ou APK; aprovação em CI ainda pendente. Branch `feature/emerald-v100-m23a-server-first-lab`, PR #19. M3.0 segue o documento `docs/V100_M30_PLAYABLE_EVOLUTION_ROADMAP_PTBR.md`, inclusive decisão 11A Brendan/May apenas. Rollback M2.2-B `5e53e40`.


## 45. M3.0-A lote consolidado — gate Windows de servidor real (2026-10-16)

**Atualização de código e testes:** teste de servidor real `tests/test_ehl8_m30_port_lifecycle.py` já integrado à suite `protocol` de `tools/emerald_auto_qa.py`; agora também exigido explicitamente no job `gui-tools` do workflow de build Windows `.github/workflows/build-v100-m23a-server-first-windows.yml`, commit `916201759ff5bd21f8e472bc7cf0132ad2a40bff`. Regressão adicional de lançamento parcial documentada no teste `tests/test_ehl8_m23a_server_first.py`, commit `2312bc278d152282e13cdcea3f3e7e19da4f8eb1`. Nenhuma mudança no save original, código GBA, batalha ou Android. **Status verificável:** conector retornou M1 Windows success no commit anterior `c3311df5` (run 38993703720), CI GBA Compare legado failure (run 38993703762), mas não expõe a lista de execuções automáticas completas de build acionadas por push. Logo **não há artefato ZIP completo desta revisão verificado**; não inventar link de download nem afirmar nova build jogável. Os testes adicionados ainda devem passar em Windows/Linux e o jogo requer QA humano. O usuário exige trabalho agrupado, sem pequenos informes. Baseline M2.2-B 5e53e40 preservada.


## 46. Correção do gate de empacotamento Windows após revisão consolidada (2026-10-16)

Na revisão integral solicitada pelo usuário, foi detectado um defeito de edição no workflow `.github/workflows/build-v100-m23a-server-first-windows.yml`: a validação do manifesto SHA256 tinha uma string PowerShell quebrada por uma quebra de linha e um fragmento duplicado após o fim do YAML. Isso podia impedir o parser/runner de chegar à compilação e ao ZIP, então nenhum artefato dessa revisão deve ser presumido válido.

**Correção aplicada:** regex de validação restaurada para uma linha, fragmento duplicado removido e arquivo reduzido ao fim correto do workflow. Commit de correção do workflow: `9ee088271015d5c9fba8d62863a0a4988fadfbd8`. O pacote continua condicionado aos jobs `game`, `gui-tools` e `portable`, à regressão Auto QA, à verificação SHA256 após extração e à ausência de arquivos `.sav`. A próxima confirmação deve vir de execução Actions no SHA exato; a edição não é prova de build verde.

**Status conservador:** ainda não foi comprovado um ZIP novo para o HEAD corrigido, nem QA humano M2.3/M3.0, nem APK Android/crossplay. Não usar artefato antigo como se contivesse os testes recentes. O rollback conhecido continua M2.2-B `5e53e40`, aprovado pelo usuário em 5/5 testes. Nenhum save pessoal ou código de gameplay foi alterado nesta correção.


## 47. Validação preventiva da sintaxe de workflows (2026-10-16)

Após corrigir o workflow de build, foi adicionada uma proteção independente em `.github/workflows/emerald-auto-qa.yml`: a matriz Windows/Linux agora instala PyYAML e faz parse sintático de todos os arquivos `.github/workflows/*.yml` antes da regressão funcional. O filtro de caminhos também inclui alterações em qualquer workflow, para que a edição de um arquivo de build seja coberta pelo verificador. Commit: `eff1b3584603684ef521b2116aea62f8f020362c`.

Esta checagem identifica YAML malformado, mas não substitui validação semântica do GitHub Actions, compilação Windows, Auto QA verde ou QA humano. O próximo gate continua sendo consultar o resultado de CI/build do SHA final e só então publicar o link de um ZIP comprovado. APK Android/crossplay e a beta jogável M3.0 continuam sem evidência de entrega nesta etapa.


## 48. Correção do shell do validador YAML em Windows (2026-10-16)

A primeira execução do novo gate preventivo revelou um problema real: no runner Windows, o step de parse YAML estava usando o shell PowerShell padrão, mas o script era sintaxe heredoc de Bash (`python - <<'PY'`). O Auto QA falhou antes de executar suas suítes; isso foi identificado nos logs do run `38994399791`. Corrigido o step para declarar explicitamente `shell: bash`, compatível com Bash do runner Windows e Linux. Commit: `3dc85234c67309520bb08909ee34aedfad366898`.

A nova revisão precisa passar pelo workflow para confirmar que o parse de todos os YAMLs funciona nas duas plataformas; ainda não há aprovação registrada deste SHA. O build completo Windows segue em execução separada e só será divulgado se todos os jobs terminarem verdes e o ZIP final tiver artifact ID real. Nenhum save, gameplay, sprites ou APK foi alterado nesta correção.


## 49. Correções guiadas pelos resultados reais do Auto QA (2026-10-16)

A execução Auto QA do commit `3dc85234c67309520bb08909ee34aedfad366898` confirmou que o validador YAML passou em Windows e Linux e que o teste real de ciclo de vida da porta passou nas duas plataformas. O relatório também revelou dois defeitos antigos/regressivos que estavam bloqueando o gate: (1) três continuadores de linha Python foram gravados com duas barras invertidas em `tests/test_ehl8_m23a_server_first.py`, causando `SyntaxError` no import; corrigido no commit `ae903037bee438316c16d72147190b476757cd7a`; (2) `tests/test_emerald_qa_lab.py` comparava o caminho `cwd` por texto, falhando no Windows quando a mesma pasta temporária aparecia em formato curto DOS 8.3; substituído por `Path.samefile` no commit `df34ebeeb220bba79262eeb7e952d43c1d09d88f`.

**Evidência anterior:** o Auto QA Windows marcou 11 PASS / 2 FAIL; Linux 13 PASS / 2 FAIL. Os dois FAIL eram essas suítes, e a nova execução precisa confirmar a correção no HEAD. O teste de porta real foi PASS em Windows/Linux, assim como protocolo, admin, reconexão e safety restantes. Não declarar Auto QA consolidado verde até os novos relatórios terminarem. Nenhum código de gameplay, sprite, SAV ou APK foi alterado.


## 50. Ajustes finais dos mocks de processo e dos perfis de backup (2026-10-16)

O relatório Auto QA Linux do run `38994445631` detalhou duas falhas em `tests/test_emerald_qa_lab.py`: o mock de processo local não implementava `wait()` (exigido pela parada ordenada do servidor) e um teste que montava o estado da sessão manualmente não preenchia a allowlist `game_profiles`, embora a produção agora só faça backup de perfis realmente lançados. Corrigido adicionando `wait()/kill()` ao mock e inicializando a allowlist no cenário que simula pós-lançamento. Commit: `48babd82f95b0c616e6099af62de7b1bcde268fe`. O ajuste é de teste, preserva a regra de não fazer backup de perfil que não foi aberto e não toca SAV real.

O outro defeito do relatório (continuação Python inválida em `test_ehl8_m23a_server_first.py`) foi corrigido no commit `ae903037bee438316c16d72147190b476757cd7a`; a divergência de caminho 8.3 do Windows foi corrigida no commit `df34ebeeb220bba79262eeb7e952d43c1d09d88f`. A revisão seguinte precisa reexecutar Auto QA e build completos; até lá, os gates continuam pendentes e não existe ZIP final declarado aprovado.


## 51. Última falha Windows do Auto QA: comparação textual de caminho (2026-10-16)

O relatório Auto QA Windows do run `38994562302` agora confirma 12 PASS, 1 FAIL e 2 SKIP; a única falha restante foi `test_failed_second_game_rolls_back_only_new_children`, cuja asserção comparava o caminho do executável por string e divergia entre caminho longo e alias DOS 8.3 do runner. A verificação foi alterada para `Path(...).samefile(...)`, sem reduzir o teste de rollback de filhos recém-criados. Commit: `28b304bf0313718b78fa569948cd4d7e7497abc3`.

Validador YAML já passa em Windows e Linux; teste de ciclo de vida da porta real também passou em ambas no relatório anterior. A próxima execução deve confirmar zero falhas de Auto QA. Build completo Windows e ZIP ainda aguardam término no SHA final; Android/APK e gameplay M3.0 seguem fora do que foi comprovado nesta etapa.


## 52. Auto QA verde em Windows e Linux após correções (2026-10-16)

Execução concluída: [Auto QA Windows + Linux, run 38994634156](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/38994634156), commit testado `28b304bf0313718b78fa569948cd4d7e7497abc3`, conclusão `success`. Relatórios de artefato confirmam **Linux: 15 PASS / 0 FAIL / 0 SKIP** e **Windows: 13 PASS / 0 FAIL / 2 SKIP** (os dois testes de fixtures nativos POSIX são intencionalmente Linux-only). O teste real de ciclo de vida da porta TCP está incluído e passou nas duas plataformas. Correções que eliminaram os defeitos detectados estão documentadas nas seções 46–51.

Esse sucesso comprova as suítes automatizadas do commit testado, não gameplay gráfico real, integridade de save dentro do jogo, APK Android ou crossplay. O build completo Windows da revisão final `364f3c2f0d04d1f3bdd9db313f45a23e79edea7c` ainda estava aguardando execução/conclusão quando esta nota foi escrita; após esta nota o novo HEAD exigirá build de mesma revisão para obter ZIP final exato. Nenhum save pessoal foi usado.


## 53. Kanto como segundo continente — primeiro incremento K0 (2026-10-20)

**Decisão nova do usuário:** adicionar a geografia de Kanto (referência FireRed) como uma segunda região do Emerald, sem substituir Hoenn. A travessia será tratada como viagem entre continentes usando o mesmo treinador, inventário e save. Pokémon Ruby não será importado por ser Hoenn redundante. A nova expansão deve preservar o projeto multiplayer Emerald Hybrid e suas preferências anteriores.

**Branch isolada:** `feature/emerald-kanto-gateway-m0` a partir da branch M2.3-A `feature/emerald-v100-m23a-server-first-lab` no commit base `59b94d1a6b2411f85b0eac8a12d31cb7b92fc73f`. Primeiro commit K0: `71e7e4ab2faeb6ef0227f0e84858472da030d0b2`. O PR novo deve mirar a base M2.3-A, sem alterar nem mesclar automaticamente PR #19. Rollback funcional histórico continua M2.2-B `5e53e40`.

**Implementado no K0 (apenas porta de entrada):** grupo `gMapGroup_Kanto` adicionado ao final de `data/maps/map_groups.json` preservando posição/IDs antigos; mapa `data/maps/Kanto_Harbor/map.json` com layout **Emerald** `LAYOUT_ISLAND_HARBOR` reutilizado; scripts novos para viajar de Slateport e voltar, por marinheiro independente do S.S. Tidal; include em `data/event_scripts.s`. Criado teste estrutural `tests/test_kanto_gateway.py` e roteiro `docs/KANTO_SECOND_REGION_FOUNDATION_PTBR.md`. Nenhum save de usuário foi lido, sobrescrito ou criado. Nada de FireRed foi copiado para esse commit.

**Ainda não implementado:** cidades e rotas reais de Kanto, tilesets e colisão FRLG, eventos/NPCs completos, mapa regional no PokéNav e Fly, história de ginásios de Kanto, encontros e teste multiplayer nesta área. O porto deve ser anunciado como **protótipo de transição**, nunca como continente completo.

**Testes e riscos:** os arquivos JSON e as referências centrais foram checados estruturalmente durante a preparação, mas ainda NÃO existe compilação aprovada, QA de mapa/câmera, colisão do novo marinheiro no porto de Slateport nem download Windows de mesmo SHA verificado. Aguardar workflow Kanto Gateway QA no commit de CI e teste manual antes de permitir merge. Eventuais falhas em mapa, script ou texto exigem correção nesta branch; não modificar save offset para forçar entrada.


## 54. Kanto como continente: rodada 1–40 e preflight da superfície (2026-10-20)

O usuário enviou 40 das 250 respostas: `1C 2A 3D 4A 5A 6B 7C 8C 9A 10B 11D 12A 13B 14A 15D 16C 17D 18B 19B 20C 21A 22A 23A 24A 25A 26A 27A 28C 29A 30A 31A 32D 33D 34D 35D 36D 37D 38D 39D 40D`. **27 específicas / 13 delegadas**; as demais **210 não estão respondidas**. Documento de interpretação `docs/KANTO_DECISIONS_001_040_PTBR.md`. Requisitos principais: várias cidades, praticamente todo exterior de Kanto, mais de 3h de gameplay real, FireRed fiel, exterior primeiro, Sevii depois, quatro insígnias, passagem de preço fixo, mesma equipe de Hoenn, apenas Windows offline inicialmente. O objetivo é ambicioso e **ainda não foi alcançado**.

Estado baseline: PR #24 K0 commit `53862a7986b1cac0eb5a2375c1d67ab1d927e371`, CI Kanto Gateway específico success nos runs `39379398555`/`39379359537`, CI geral legado failure no run `39379398487` (não equivale a falha do cross-build Kanto). Mapa Kanto_Harbor usa tiles Emerald provisórios; nenhum mapa real de FireRed foi importado ainda.

Branch da próxima etapa: `feature/kanto-v01-decisions-import-preflight`, derivada da branch K0 sem mexer nela. Commits de código: `c2eb7386d6b9da8f307de14f75d653e2dc9f5f12` (quatro insígnias + tarifa P500 com confirmação e saldo), `d1928d18d43f189911710fefd7568b26c459838f` (auditor source-only) e `d10dd168a774206bc4c193225f82ccd2c092366e` (workflow de teste, checkout FireRed pinado e cross-build). Novos arquivos: `tools/kanto/preflight.py`, `tests/test_kanto_preflight.py`, `.github/workflows/kanto-v01-preflight.yml` e especificação. Alterados: `data/maps/SlateportCity_Harbor/scripts.inc`, `tests/test_kanto_gateway.py`, AI_README. **Nenhum save, tileset ou mapa de Hoenn foi reescrito nesta etapa.**

Próximos passos: conferir logs/relatório/CI no HEAD; corrigir falhas sem esconder status; porter tilesets, colisão e layouts originais, conectar Verdadeira Vermilion e demais exteriores, interiores úteis, encontros/batalha/cura, save e retorno seguro; validar Windows realmente jogável, depois LAN/Android. Último rollback funcional documentado `5e53e40`. A escolha #19B (retorno ao último centro de Hoenn) e #20C (fallback cidade inicial em falhas) ainda não estão implementadas; o porto provisório retorna a Slateport. Não marcar meta de 3h como concluída só com reporte estático. CI ainda pendente até sua execução.

## 55. Kanto V0.2: 250 decisões completas e exterior real (2026-10-20)

Respostas 250/250 (34 escolhas A/B/C, 216 delegações D) em docs/KANTO_DECISIONS_250_PTBR.md; esta especificação substitui as 40/250 anteriores. Branch feature/kanto-v02-real-vermilion-exteriors, PR #26 (draft) sobre PR #25.
O script tools/kanto/import_exteriors.py utiliza pret/pokefirered SHA ce6406d8c2eaf46d543c8a2606de0c3cb1951982 para gerar 38 mapas externos reais, paletas/tilesets/atributos e encontros selvagens de FireRed com IDs de Kanto. Mudanças no motor isolam divisão 640/7 do FireRed contra 512/6 do Emerald original. O ferry conduz até Vermilion com posições verificadas contra colisão; há cura e batalha Pidgey de teste, não NPCs originais.
Novo special Kanto_ReturnToHoennHealWarp retorna ao último local de cura Hoenn armazenado em save, fallback Slateport para grupo inválido. Exige QA real de save e retorno. A PR guarda gerador reproduzível, não copia 38 binários completos antes da geração local/CI.
CONTINUA INCOMPLETO: interiores, eventos, treinadores, ginásios, música original, QA gráfico/mapa real e garantia de 3h de gameplay. Não declarar Kanto completa. Rollback M2.2-B 5e53e40 e PRs #19/#24/#25 preservados.

## 56. Kanto V0.3 — Centros Pokemon e mercados regionais (2026-10-20)

Nova branch feature/kanto-v03-regional-services criada a partir do commit Kanto V0.2 compilado 3caf970e680487b6d6062f9165a6f772df498bf1. A PR #26 original permanece como marco anterior. O gerador tools/kanto/import_exteriors.py preserva os 38 exteriores de FireRed e amplia os interiores 1F, adicionando 15 Centros Pokemon/Poke Marts de outras cidades além dos dois já adicionados em Vermilion (total 17). São os layouts originais FRLG LAYOUT_POKEMON_CENTER_1F e LAYOUT_MART e a arte de gTileset_KantoBuilding, com portas de ida e volta ligadas pelos índices gerados.
Ao entrar nos Centros a enfermeira chama Common_EventScript_PkmnCenterNurse do Emerald. As lojas usam pokemart com estoque genérico temporário: migrar itens e NPCs específicos da origem em fase posterior. Respawn/heal Kanto ainda não possui localização de cura regional persistente para não sobrescrever o último destino de cura de Hoenn; em caso de derrota retorna ao centro anterior do jogo. Salvar/carregar dentro dos edifícios exige QA humano. Centro 2F não está integrado para evitar entrada em áreas incompletas.
Workflow dedicado .github/workflows/kanto-v03-regional-services.yml valida 56 mapas totais no grupo Kanto (1 cais + 38 exteriores + 17 interiores) e testa correspondência de warps e scripts, além de compilar Windows. NÃO mesclar se workflow falhar. Todas as decisões 250/250 seguem em docs/KANTO_DECISIONS_250_PTBR.md. Sem ginásios, cavernas e missões completas; jamais chamar Kanto completa ou 3h comprovadas.

## 57. Kanto V0.4 e V0.5 — lojas originais e acessos Saffron (2026-10-20)

V0.4 branch `feature/kanto-v04-original-mart-stocks`, draft PR #30: para os oito Poké Marts de Kanto, o importador `tools/kanto/import_exteriors.py` passa a ler os itens na ordem original de `pret/pokefirered` (SHA `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`), validando a existência de cada constante na versão atual Emerald e a terminação do estoque. CI V0.4 inclui fixture do parser e comparação 8/8 antes do build.

V0.5 branch `feature/kanto-v05-saffron-gates` (encadeada sobre V0.4): quatro edifícios de passagem entre Saffron City e Route 5/6/7/8 importados com layout original de FireRed; `gTileset_KantoGenericBuilding2` convertido, novos warps registrados em ambas as extremidades sem interferir no Emerald original. **60 mapas no grupo Kanto**; primeiro 56 IDs antigos preservados para estabilidade de saves/protocolo. Relatório e QA `docs/KANTO_V05_SAFFRON_GATES_PTBR.md`; workflow `kanto-v05-saffron-gates.yml`.

IMPORTANTE: o compilador pode validar a estrutura, mas **não certifica** movimento, salvamento, guerra de colisões, scripts, NPCs originais ou 3h de gameplay. Ainda faltam dungeons, centros 2F e whiteout regional. PR #19/#24/#25/#26/#28/#30 não são mescladas por esta mudança. Rollback M2.2-B `5e53e40` preservado. 

## 58. Kanto V0.6 — florestas/cavernas, batch real de nove mapas (2026-10-21)

Autorização do usuário: liberdade integral de decisões técnicas preservando as 250 respostas; continuar sem novas perguntas, mas não declarar implementação completa sem QA. Branch `feature/kanto-v06-forest-moon-diglett` a partir do commit V0.5 `26c4c61d070804663e88fcac875904855f4c4089`, PR em draft encadeada na PR #31. Importador `tools/kanto/import_exteriors.py`: 9 mapas adicionais de FireRed (ViridianForest, dois portões Route2, três partes Diglett Cave, três andares Mt Moon) com blocos/tilesets/warps bidirecionais originais e encontros FireRed. Total Kanto 69 mapas (cais, 38 exteriores, 17 serviços, 4 portões Saffron, 9 áreas dungeons). **IDs anteriores 0–59 imutáveis**, novos 60–68. Verificação por checksum/warps/espécies e compilação Windows na workflow `kanto-v06-forest-moon-diglett.yml`. Documento `docs/KANTO_V06_CAVES_FOREST_PTBR.md`.

Não portados: NPCs, itens, Rocket, treinadores, puzzles originais, Centro 2F, heal/whiteout regional, ginásios, missão completa, animações de tile, QA de colisão no jogo, Android e multiplayer Kanto. Nem 50% de gameplay foi validado. Regra: não mesclar sem CI exata + testes de save e gameplay. Rollback histórico M2.2-B `5e53e40` preservado.
