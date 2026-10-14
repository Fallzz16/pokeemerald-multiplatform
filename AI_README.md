# AI README — Emerald Hybrid Multiplayer: passagem de contexto entre IAs
> **LEITURA OBRIGATÓRIA ANTES DE EDITAR QUALQUER COISA NESTE REPOSITÓRIO.**
> Atualizado em 2026-10-13 (planejamento v0.8, decisões **1–100** confirmadas). Documento específico deste fork, para evitar recomeços, erros de branch, perda de recursos ou afirmações de testes inexistentes.

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

## 3. Decisões aprovadas pelo usuário (1–100)

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
