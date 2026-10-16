# Emerald Hybrid v1.0 — especificação aprovada pelo usuário (V1-01 a V1-72)

Esta especificação **não substitui** as decisões históricas #1–116 em `docs/LAN_V080_ARCHITECTURE.md` e `docs/LAN_V080_MEGA_DESKTOP_PASS1.md`. Use prefixo **V1-** para cada decisão desta rodada. Todas as 72 escolhas foram explicitamente confirmadas pelo usuário em 2026-10-15: **V1-04C** e **todas as demais V1-xxA**.

## Rodada 1 — foco da release

| Decisão | Escolha | Comportamento aprovado |
|---|---|---|
| V1-01 | A | Windows primeiro, Android depois. |
| V1-02 | A | Jogo estável e multiplayer LAN funcional. |
| V1-03 | A | Dois jogadores aprovados, preparar expansão para quatro. |
| V1-04 | **C** | Prioridade de desenvolvimento para batalhas; trocas existentes preservadas e expansão de trocas depois. |
| V1-05 | A | Hospedar jogando e servidor dedicado. |
| V1-06 | A | Perfis locais, conta online opcional. |
| V1-07 | A | Duas instâncias reais e múltiplas identidades simuladas. |
| V1-08 | A | Redesign profissional do launcher. |
| V1-09 | A | Backups automáticos e isolamento de perfis. |
| V1-10 | A | Instalador e ZIP portátil Windows. |
| V1-11 | A | Atualização disponível com aceite do usuário. |
| V1-12 | A | Lançar somente após QA real e bugs críticos resolvidos. |

## Rodada 2 — experiência e prioridades

| Decisão | Escolha | Comportamento aprovado |
|---|---|---|
| V1-13 | A | Campanha individual; história e progresso próprios. |
| V1-14 | A | Sprites remotos com movimento, direção e animação. |
| V1-15 | A | Consolidar batalhas 1v1 P2P antes de migrar ao dedicado. |
| V1-16 | A | Batalhas tradicionais 1v1 na v1.0. |
| V1-17 | A | Interagir com avatar próximo e abrir menu. |
| V1-18 | A | IP, PIN e histórico de servidores recentes. |
| V1-19 | A | Lobby visual: jogadores, Ready, Start, status. |
| V1-20 | A | Reconectar automaticamente por tempo limitado. |
| V1-21 | A | Host vê jogadores, remove, bloqueia entradas, fecha sala. |
| V1-22 | A | Login online opcional para identidade/amigos; saves locais. |
| V1-23 | A | Painel abre dois Emeralds com perfis isolados. |
| V1-24 | A | Até 50 identidades fictícias em rodadas de dois. |
| V1-25 | A | Bots simulam entrada, movimento, desconexão, reconexão. |
| V1-26 | A | Métricas, latência, erros, relatório de QA. |
| V1-27 | A | Páginas Início/Jogar/Multiplayer/Perfis/Configurações. |
| V1-28 | A | Assistente de criação/importação de perfil. |
| V1-29 | A | Backup antes de operações arriscadas e após encerramento normal; o requisito histórico de salvamento manual permanece. |
| V1-30 | A | Launcher moderno inspirado em Pokémon, animações leves. |
| V1-31 | A | Resolução, escala, FPS, áudio e presets. |
| V1-32 | A | CI, duas janelas reais, LAN em dois PCs, saves. |

## Rodada 3 — mecânicas e segurança

| Decisão | Escolha | Comportamento aprovado |
|---|---|---|
| V1-33 | A | Convite de batalha pelo menu do avatar, P2P. |
| V1-34 | A | Convites permitidos mesmo entre mapas diferentes. |
| V1-35 | A | Regras tradicionais do Emerald. |
| V1-36 | A | Resultado da batalha sem progressão especial no save. |
| V1-37 | A | Desconexão em batalha encerra o duelo com segurança. |
| V1-38 | A | Renderizar avatar só em mesmo mapa/área visível. |
| V1-39 | A | Reutilizar sprites e animações existentes. |
| V1-40 | A | NPCs, eventos e progresso individuais. |
| V1-41 | A | Sprites remotos sem colisão. |
| V1-42 | A | Emotes e mensagens rápidas predefinidas. |
| V1-43 | A | Reservar vaga por 60 segundos para reconexão. |
| V1-44 | A | START após dois participantes Ready. |
| V1-45 | A | Sobrevivente continua jogando se o par sair. |
| V1-46 | A | Admin: lista, expulsar, bloquear e encerrar. |
| V1-47 | A | Falha de multiplayer: diagnóstico e opção offline. |
| V1-48 | A | Login opcional com provedor confiável, sem senha própria. |
| V1-49 | A | Identidade e amigos online, saves locais. |
| V1-50 | A | Aba opcional de desenvolvedor. |
| V1-51 | A | Perfis de teste copiados e isolados em diretórios temporários. |
| V1-52 | A | Relatórios exportáveis com conexões, latência e falhas. |

## Rodada 4 — acabamento e publicação

| Decisão | Escolha | Comportamento aprovado |
|---|---|---|
| V1-53 | A | Avatar quando próximo, lobby quando distante para convites. |
| V1-54 | A | Aceitar/recusar convite de batalha com timeout. |
| V1-55 | A | Retorno seguro à sessão EHL8 depois de batalha P2P. |
| V1-56 | A | Token temporário vinculado à sessão para reconexão. |
| V1-57 | A | Launcher com menu lateral e páginas. |
| V1-58 | A | Início com perfil, Jogar, servidor e novidades. |
| V1-59 | A | Assistente de primeira execução. |
| V1-60 | A | Tema Emerald escuro e alternância claro/escuro. |
| V1-61 | A | Português-BR e inglês. |
| V1-62 | A | Escala de texto, teclado e contraste. |
| V1-63 | A | Dois jogos reais com processos/perfis temporários. |
| V1-64 | A | Apagar dados de teste com confirmação, preservar relatórios. |
| V1-65 | A | Empacotar dependências, sem exigir instaladores externos. |
| V1-66 | A | Migração opcional, backup e possibilidade de rollback. |
| V1-67 | A | Canais Estável/Beta, atualização confirmada. |
| V1-68 | A | Integridade e restauração após falha de atualização. |
| V1-69 | A | Erros legíveis, reparo e exportação de diagnóstico. |
| V1-70 | A | Sem CMD normalmente, console opcional para desenvolvedor. |
| V1-71 | A | Diagnósticos locais, envio só com consentimento. |
| V1-72 | A | Release final só após testes reais e aprovação do usuário. |

## Resoluções técnicas aprovadas para planejamento

- **V1-04C e V1-15A:** priorizar batalha 1v1; manter trocas antigas operando pelo Cable Club até uma futura integração. Não remover transporte nem funcionalidade anterior.
- **V1-34A + V1-38A + V1-53A:** convite local pelo avatar e remoto pelo lobby, preservando culling de sprites.
- **V1-37A + V1-43A + V1-56A:** reconectar a exploração com reserva/token; não prometer retomada de duelo interrompido.
- **V1-44A + V1-45A:** dois Ready para iniciar; sala pode continuar com um conectado após saída.
- **V1-22A/48A:** provedores externos apenas como login opcional, nunca bloquear offline por indisponibilidade de Internet.
- **V1-24A/63A:** simulação de 50 identidades em rodadas não expande o limite real simultâneo de dois.
- **V1-29A + histórico #79A:** a implementação deve proteger saves após eventos seguros de gravação manual e no encerramento; nunca copiar arquivo durante escrita ou chamar autosave indevido.

## Marcos e aceite

| Marco | Implementar | Aceite requerido |
|---|---|---|
| M0 | Baseline, CI, isolamento, documentação e rollback. | Não alterar jogo anterior, relatório honesto sobre failures. |
| M1 | Laboratório 2 instâncias + backups/perfis isolados. | Duas janelas reais e dois saves independentes no Windows; testar offline/localhost. |
| M2 | EHL8 2 jogadores, lobby, reconexão e administração. | QA em 2 PCs com movement/warp/disconnect/rejoin. |
| M3 | Convites + batalhas 1v1 via P2P. | Um duelo completo, retorno ao mapa e saves íntegros. |
| M4 | Bots e 50 identidades em rodadas + relatórios. | Cenários repetíveis, sem tocar saves reais. |
| M5 | Launcher profissional, contas opcionais, idiomas e acesso. | UX sem consoles, offline sem login. |
| M6 | Instalador, portátil, atualização verificada e rollback. | Instalação/migração/rollback testados. |
| M7 | Release candidate e regressões. | Aprovação CI pertinente, hardware Windows e usuário. |

**Regra de publicação:** nenhum workflow verde substitui teste de duas instâncias reais; nem o ZIP de laboratório constitui o instalador final v1.0. Enquanto estes gates não passarem, PR #10 permanece draft.

## M1.1 concluído em fonte — 50 identidades EHL8 por rodadas

- Modo de testes protocol-only de 25 pares (50 identidades), nova ação gráfica do Lab, relatório e logs, sem salvar dados do jogo.
- Builds Windows terão `EmeraldQALab.exe` e `EmeraldQABots.exe` separados, ambos incluídos no ZIP adicional; ainda requer CI e testes reais após upload.
- O teste do servidor de produção roda apenas no repositório completo; no pacote de código-fonte isolado ele será ignorado de forma explícita.
- Não foi feita migração, mudança no protocolo de produção, implementação de batalha P2P/EHL8, reconexão de 60 segundos, suporte para 4 jogadores, nem alteração de saves.
