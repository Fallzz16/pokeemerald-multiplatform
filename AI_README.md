# AI README — Emerald Hybrid Multiplayer: passagem de contexto entre IAs
> **LEITURA OBRIGATÓRIA ANTES DE EDITAR QUALQUER COISA NESTE REPOSITÓRIO.**
> Atualizado em 2026-10-13 (planejamento v0.8). Documento específico deste fork, para evitar recomeços, erros de branch, perda de recursos ou afirmações de testes inexistentes.

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

## 3. Decisões aprovadas pelo usuário (1–50)

As letras são exatamente as respostas do usuário. Reconsultar a descrição de cada decisão em `docs/LAN_V080_ARCHITECTURE.md` antes de interpretar letra isoladamente.

- **1–10:** 1B 2A 3B 4B 5B 6C 7A 8B 9A 10A
- **11–20:** 11A 12B 13B 14B 15A 16A 17A 18A 19A 20B
- **21–30:** 21A 22A 23C 24A 25C 26B 27A 28C 29A 30A
- **31:** objetivo de suporte a celulares com 4 GB+ RAM (**sem garantia universal**).
- **32:** usuário aprovou gameplay real da v0.7.2.1.
- **33–40:** 33C 34A 35A 36A 37A 38A 39A 40A
- **41–50:** 41B 42A 43C 44A 45B 46A 47B 48A 49A 50C

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

**Próxima decisão:** coletar respostas 51+ sobre save / lobby / segurança / discovery antes de congelar session-v1. Este documento deve ser atualizado com as respostas posteriores.

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
- **Próximo passo:** colher respostas 51–75; congelar session-v1; implementar SaveProfileManager atrás de feature flag, com testes offline e backups.
