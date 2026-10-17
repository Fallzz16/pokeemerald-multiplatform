# Emerald Hybrid M3.0 — Playable Evolution

**Estado:** especificação técnica aprovada pelo usuário; NÃO confundir com implementação ou build testada.
**Base preservada:** PR #19, branch `feature/emerald-v100-m23a-server-first-lab`; rollback de gameplay: M2.2-B `5e53e40` (QA humano 5/5).
**Distribuição:** Windows EXE e Android APK. ROM GBA não é alvo de distribuição, e Compare GBA legado não bloqueia a aceitação dos apps.

## Decisões confirmadas

Rodada 1: **1D 2D 3D 4D 5C 6D 7D 8D**.
Rodada 2: **9D 10D 11A 12C 13D 14D 15C 16D 17D 18D 19D 20D 21D 22D 23D 24D**.

- 1D: grande atualização equilibrada; 2D: mundo compartilhado + missões cooperativas, preservando o solo; 3D: convites, aceite, recusa e revanche 1v1 antes de duplas/espectadores; 4D: convite e prévia de troca com confirmação dupla e prevenção contra duplicação; 5C: emotes, perfis, amigos e convites, **sem exigir grupos**; 6D: salas LAN com permissões, reconexão e arquitetura extensível à internet; 7D: saves offline e transição protegida; 8D: visuais opcionais escaláveis.
- 9D: launcher moderno completo; 10D: menus modernos opcionais, interface clássica selecionável; **11A: apenas Brendan e May; NÃO desenvolver roupas/cabelo/acessórios, cosméticos ou sincronização cosmética**; 12C: perfis e amigos com convites rápidos, sem histórico obrigatório; 13D: explorar com NPCs/eventos/co-op, mantendo campanha; 14D: objetivos compartilhados, recompensa individual, histórias co-op depois; 15C: casual/clássico/desafio, sem impor regras especiais multiplayer; 16D: QoL preservando equilíbrio; 17D: meta 60 FPS PC modesto, Android econômico (meta, não garantia); 18D: presets + controle avançado + detecção; 19D: touchscreen adaptável e suporte a controles Bluetooth; 20D: Windows primeiro, arquitetura compartilhável, testar crossplay progressivamente; 21D: Auto QA de entrada de controle, rede, dois jogadores, screenshots e saves isolados; 22D: backups/recuperação seguros; 23D: lotes grandes com QA e ZIP completo; 24D: beta requer solo + EHL8 estável + convites batalha/troca + reconexão + saves e QA real.

## Dependências e marcos de implementação

### M3.0-A — Desktop jogável reproduzível (bloqueia demais)
- Construir ZIP Windows de SHA único, validar jogo + launcher + Lab + EHL8, rodar em PC real.
- Corrigir reinício, porta 45680, saída limpa e slots QA_A/QA_B; save original nunca escrito pelo Lab.
- Auto QA automático por fluxo real da aplicação quando tecnicamente possível, separado dos bots EHL8 e de mocks.
- Critérios: EXE abre e continua jogo offline; 2/2 movimento e avatar corretos; servidor fechado libera porta; sessões e saves íntegros; ZIP completo com download exato.

### M3.0-B — Lobby e interações seguras
- Pronto/Cancelar individual, convites e respostas; sem iniciar sala sozinho.
- Lista de amigos/perfis, emotes, indicadores, permissões e bloqueio de entradas; proteção contra spam/replay.
- Critérios: testes da máquina de estados de ambos jogadores, reconexão, kick, timeout; QA manual dos botões.

### M3.0-C — Gameplay multiplayer
- Batalhas P2P 1v1 (convite/aceite/recusa/revanche), retorno ao overworld; preservação do Cable Club legado.
- Trocas (prévia + aceites duplos + commit idempotente/recuperável) com cópias e backups de QA.
- Co-op simples com objetivo compartilhado e recompensa **individual**, sem duplicação de item/Pokémon.
- Critérios: testes reais de batalhas e trocas 2 PC; nenhum travamento ao recusar/reconectar; integridade salva antes/depois.

### M3.0-D — UX/performance e qualidade
- Launcher, menus opcionais, presets gráficos, navegação, QoL e modos de dificuldade como opções; preservar o visual GBA.
- Brendan/May **somente**. Otimizações medidas no Windows com modo econômico e regressão de sprites/paletas.
- Critérios: comparações de FPS, estabilidade, menus, input e perfis sem regredir M2.2-B.

### M3.0-E — APK e crossplay
- Investigar a rota de portabilidade existente (código nativo e ferramentas Android) antes de assumir estratégia de compilação; não converter EXE em APK por renomeação.
- Touch configurável, resolução/escalonamento, controle Bluetooth, arquivos app-private; reconexão Wi-Fi e LAN Android ↔ Windows.
- Critérios: APK instalável em Android real, perfil/saves migráveis com consentimento, jogabilidade solo, sessão LAN crossplay validada por duas máquinas, métricas de memória e estabilidade.

### M3.0-F — Beta pública de testes
- Builds ZIP/APK da mesma revisão de protocolo, hashes/manifesto de compatibilidade, atualização com rollback.
- Completar gate 24D no mundo real: solo/saves, 2 jogadores, convites batalha e troca, reconexão; evidências do Auto QA e QA humano.
- Documentar limitações honestamente; **não declarar todos os marcos concluídos apenas pelo planejamento**.

## Regras técnicas e testes
- Não misturar executáveis de commits diferentes. Não distribuir .sav. Backups atômicos, compatibilidade de saves e rastreabilidade de SHA.
- Builds Windows e Android são gates de produto separados. Um não aprova automaticamente o outro.
- Testes de protocolo simulados NÃO equivalem a jogadores navegando a Hoenn; GBA Compare legado não bloqueia Windows/Android.
- Sempre adicionar testes antes de modificar protocolo/gameplay; preservar M2.2-B para rollback e atualizar `AI_README.md` por incremento.
- O prazo e a quantidade de commits não são critérios de aceitação: só comportamento reproduzível com evidência.

## Entrega imediata após esta especificação
1. Diagnosticar builds do PR #19 e obter artefato completo da revisão aprovada.
2. Executar QA da M2.3-B2 real em Windows e corrigir defeitos antes de ampliar lobby.
3. Só então iniciar código M3.0-A/B; sem perguntas adicionais, salvo incompatibilidade de decisões ou bloqueio real.
