# Emerald Hybrid — auditoria orientada à beta multiplayer (19/10/2026)

> **Estado: engenharia em andamento; NÃO É UMA BETA APROVADA DE GAMEPLAY.**  
> O único escopo autorizado é multiplayer/online do Emerald Hybrid existente, sem quests, histórias, mapas, Pokémon, modos ou outras expansões de conteúdo. QA Lab continua ferramenta exclusiva de teste, distinta do launcher final.

## 1. Método e honestidade da cobertura

Fonte auditada: repositório `Fallzz16/pokeemerald-multiplatform`, SHA de partida `d9a7d92263b64cb4a073d45ab3cb2e1386047ad1`, branch base `feature/emerald-m30-pin-hardening-decisions-20261019`; incremento nesta branch `feature/emerald-m30-beta-launch-safety-20261019`.

A API GitHub retornou uma **árvore recursiva completa de 13.590 entradas, sem truncamento**. Contagens dos arquivos por grupo: `graphics/` 5.730, `data/` 3.551, `sound/` 1.303, `src/` 499, `include/` 335, `tools/` 121, `tests/` 27, `scripts/` 27, `.github/` 25 e `docs/` 23 (além de outras pastas e arquivos de raiz). **Inventariar a árvore NÃO equivale a ler individualmente todos os arquivos**: análise semântica priorizou documentos obrigatórios, servidor EHL8, cliente nativo, ponte serial, launcher, QA Lab, saves, SDL2, workflows, testes e Android. Conteúdo de milhares de gráficos/sons/mapas não foi inspecionado um a um. Não afirmar auditoria linha a linha de tudo, ausência total de bugs ou testes gráficos executados pela IA.

### Componentes e responsabilidades confirmadas

| Área | Arquivos | Situação baseada no código |
|---|---|---|
| Laboratório exclusivo QA | `tools/emerald_qa_lab.py`, `tools/emerald_qa_lobby.py`, `tests/test_emerald_qa_lab.py` | Existem QA_A, QA_B, iniciar servidor sem jogo, entrar individualmente, Lobby ao vivo e testes isolados. Lab liga-se a **127.0.0.1** e não é o frontend remoto final. |
| Launcher final Windows | `tools/emerald_launcher.py`, `tests/test_emerald_launcher.py` | Disponibiliza offline, Cable Club P2P e EHL8 via IP + PIN; hospedagem EHL8 em `0.0.0.0`. Algumas mensagens antigas tornavam fácil confundir host P2P com sala de presença EHL8. |
| Núcleo dedicado | `tools/emerald_session_server.py`, `src/lnet/lnet_session_v1.c` | EHL8 real para 1–2 slots, PIN, lobby/READY, START, presença, heartbeat, reconexão opt-in; **não implementa batalha/troca no mesmo protocolo**. |
| Cliente de jogo | `src/lnet/lnet_session_client.c`, `src/link.c`, `src/platform/sdl2.c` | Cliente não bloqueante, handshake, heartbeat, dados de avatar remoto, carregamento de perfil específico. Sprite/gameplay REAL ainda precisa QA humano. |
| Multiplayer anterior | `src/lnet/lnet_link.c`, `src/lnet/lnet_sio.c`, `src/lnet/lnet_presence.c` | P2P/Cable Club separado de EHL8; não misturar streams nem afirmar que convites de PvP/troca EHL8 estão prontos. |
| Saves | `src/profile/save_profiles.c`, `tools/emerald_profilectl.c`, `tests/test_save_profiles.c` | Perfis, locks, cópia isolada e backups; **validação estrutural de setores apenas**, ainda sem comparação de checksum dos payloads antes de importar/restaurar. |
| Build e entrega | `.github/workflows/build-v100-m23a-server-first-windows.yml`, `.github/workflows/emerald-auto-qa.yml` | Testes e ZIP Windows com SHA, hash-manifesto, extração de verificação e bloqueio de saves no pacote. Isto não é QA de usuário. |
| Android | `android/app/build.gradle`, `android/app/src/main/cpp/CMakeLists.txt`, `.github/workflows/build-lan-hybrid-android.yml` | `abiFilters 'armeabi-v7a'`, workflow legado rotulado v0.7.2.1; **não há comprovação de APK ARM64 nem EHL8 atual em Android/crossplay**. |

## 2. Bloqueios e prioridades — sem marketing

### P0 — antes de chamar de beta jogável completa

1. **Gameplay real Windows em duas máquinas:** executar o ZIP de um mesmo SHA, com contas/saves separados; testar Windows host/cliente na rede, dois sprites, 30 s conectado sem travar, colisão/culling, transições, erro de rede, save/reabertura e logs; repetir na VM/rede física. Mock EHL8 e CI NÃO substituem isso.
2. **Integração de batalha e troca com a sala EHL8:** o EHL8 atual só transporta sessão/presença/poses, enquanto o Cable Club é P2P separado. Precisamos definir handshake de convite/aceite/recusa, entrada/saída do link existente e rollback seguro de trocas. Não afirmar que já existem.
3. **Saves suficientemente protegidos:** import/backup/restore devem checar dados além da estrutura; o validador nativo ainda não confere checksums internos. A função de checksum do jogo usa **tamanhos reais da região em `sSaveSlotLayout`**, que podem variar com estruturas do fork; implementar e testar em incrementos posteriores com fixtures fiéis, não reaproveitar magicamente tamanho fixo 3968 em todos os IDs. Não tocar saves pessoais.

### P1 — confiabilidade e UX de primeiro teste remoto

4. **Falha no PIN ao iniciar processo:** o launcher anterior enviava PIN para processo com `stdin.write/flush` mas, caso falhasse antes de registrar o `Popen`, não encerrava o filho. Nesta branch foi adicionado `deliver_pin_or_terminate`, com encerramento/espera/kill limitado, testes de escrita bem-sucedida, BrokenPipe e timeout; usado tanto no servidor quanto no jogo.
5. **Separação EHL8 x P2P:** botões de launcher alterados para explicitar que “HOST P2P” não cria sessão de presença; “CRIAR SALA” é servidor EHL8. A criação de servidor e depois entrada pelo próprio IP continuam **duas operações intencionais** por enquanto.
6. **Lobby do launcher para humanos:** o Lab já tem START admin manual, mas o launcher final ainda usa o modo EHL8 básico com auto READY/START; controles bonitos de PRONTO/CANCELAR e START pelo host pertencem a incremento posterior com testes de protocolo. Não transplantar controles técnicos do Lab para o jogador.
7. **Teste entre redes:** LAN privada; para casas diferentes, VPN privada de acesso restrito e teste de firewall; NÃO fazer port-forward de EHL8, pois PIN de seis dígitos via TCP não criptografa nem autentica endpoints de forma robusta.
8. **QA automatizado do launcher:** incluído `test_emerald_launcher.py` na suíte `safety` do Auto QA e no job Windows `gui-tools`. Assim uma falha de spawn/cleanup bloqueia artefato completo.
9. **CI mais eficiente:** workflows da branch agora possuem `concurrency` por fluxo/ref, cancelando commits obsoletos. É adequado para branch de desenvolvimento; nunca usar o mesmo grupo para builds estáveis independentes.

### P2 — depois do Windows realmente funcional

10. Modernizar Android: provar jogo solo APK atual, EHL8 nativo, arquitetura ARM64 viável, saves app-private e crossplay; jamais assumir com base no antigo APK ARMv7.
11. Medir FPS real, tempo de entrada, RTT/jitter, 60 s de reconexão e quedas sem corromper arquivos. Metas não substituem dados.
12. Release final: nome de versão controlado, changelog verificável, hashes de ZIP, rastreio exato de SHA e, quando versão destinada ao público, *artifact attestations* verificadas; manter rollback. GBA Compare legado pode continuar vermelho, mas precisa ter escopo/razão documentados.

## 3. Critérios verificáveis para nome da versão

| Rótulo | Critério | Estado |
|---|---|---|
| **Preview técnico EHL8** | Builds Windows + socket/lobby/bots e protocolo sem evidência de gameplay humano | **Já existe**, e o código dessa etapa foi executado por CI |
| **Candidato a beta de exploração** | Dois PCs com saves QA diferentes, movimentação de sprites, reiniciar, sair, reconectar, solo intacto | **Não comprovado** neste chat |
| **Beta jogável (escopo aprovado M3.0 #24D)** | Critérios anteriores + convite de batalha 1v1 e trocas com confirmação/recuperação, QA humano aprovado | **NÃO pronta** |
| **Beta Android/crossplay** | APK Android atual, instalação e saves seguros, controles, conectividade Windows/Android real | **NÃO comprovada** |

**Nenhuma etapa deve ser promovida automaticamente pela contagem de commits.** “60 FPS em PC modesto” e “4 jogadores” são metas posteriores; servidor EHL8 atual tem 2 slots.

## 4. Roteiro de QA humano — versão Windows atual

- Em cada computador, baixar **o mesmo artefato ZIP de uma execução única** e verificar `REVISAO_EXATA.txt`, hashes e que nenhum `.sav` foi distribuído.
- Extrair em pasta vazia, não substituir instalação antiga. Usar **perfis de teste**, não a cópia única do progresso real.
- Host: abrir `EmeraldLauncher.exe`, criar save teste, escolher PIN de 6 dígitos e `CRIAR SALA`. Confirmar serviço na porta 45680 e 0/2 sem jogo.
- Host: ativar “Entrar via servidor dedicado EHL8”, usar `127.0.0.1` e PIN, clicar ENTRAR. Convidado: IP LAN/VPN privada do host, mesma porta/PIN; 1/2 → 2/2.
- Verificar que o servidor EHL8 do **launcher final** pode auto-iniciar a sessão quando ambos enviarem READY. Não exigir o botão manual START do QA Lab nesse fluxo.
- Aproximar os personagens no mesmo mapa, movimentar, transitar, ficar parado 30+ segundos e checar posições sem sprites duplicados. Testar desconexão/saída, reinício de host, volta offline e continuidade dos saves.
- Anotar comportamento observado, FPS, logs de jogo e servidor, hash do ZIP e reprodução de qualquer problema **sem incluir o PIN nem saves pessoais**.
- VM com NAT/Host-Only fornece validação preliminar de rede; exige novo teste em 2 PCs físicos antes do aceite.

## 5. Pesquisa que ajuda de verdade

1. **GitHub Actions Concurrency**: documentação oficial recomenda `group: ${{ github.workflow }}-${{ github.ref }}` para cancelar somente execuções antigas do MESMO workflow/branch. Fonte: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
2. **GitHub Artifact Attestations**: associam binários a commit/workflow, verificáveis pelo `gh attestation verify`; é controle de proveniência, **não auditoria de código nem garantia contra bugs**. Fonte: https://docs.github.com/en/actions/concepts/security/artifact-attestations
3. **Tailscale privado com convidados**: pode conectar hosts em casas diferentes de forma criptografada, com controle de acesso, sem publicar porta do jogo; ainda é preciso testar EHL8 e firewall. Fonte: https://tailscale.com/docs/use-cases/personal-or-at-home-use/share-private-game-server
4. **SDL2 integer scale**: recurso já usado no projeto para preservar pixel art; não arriscar refatoração gráfica grande antes da beta, medir em hardware de verdade. Fonte: https://wiki.libsdl.org/SDL2/SDL_RenderSetIntegerScale
5. **Pret pokeemerald save**: `src/save.c` usa tamanhos por setor derivando de `SaveBlock1/2` e storage, indicando por que checksum não deve ser acrescentado cegamente por um tamanho universal. Fonte: https://github.com/pret/pokeemerald/blob/master/src/save.c

## 6. Registro de alteração deste incremento

**Branch nova** `feature/emerald-m30-beta-launch-safety-20261019`; base `d9a7d92263b64cb4a073d45ab3cb2e1386047ad1` (PR #20). **Modificados:** `tools/emerald_launcher.py` (PIN/cleanup e clareza EHL8), `tests/test_emerald_launcher.py` (+3 testes), `tools/emerald_auto_qa.py` (teste incluído), workflows de QA e ZIP Windows (gate launcher, evitar builds redundantes), `AI_README.md` (passagem de bastão). **Adicionado:** este relatório. **Removido:** nada. **Gameplay, saves, servidor EHL8, cliente nativo, QA Lab e APK:** não alterados nesta branch.

**Estado dos testes:** consultar sempre o GitHub Actions do SHA FINAL, não reutilizar aprovação de commit antigo; Auto QA e build Windows devem concluir. QA humano Windows/VM/segundo PC segue pendente. PR ficará em rascunho; sem merge nem release final sem aceite manual.

**Rollback:** não tocar no PR #19 nem no PR #20; o baseline antigo aprovado pelo usuário é M2.2-B `5e53e40`. Nunca sobrescrever saves ou trocar EXEs de versões diferentes.
