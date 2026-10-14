# Emerald Hybrid v0.8 — MEGA atualização, incremento 1 (Windows)
> **Status: implementação experimental, somente primeira etapa.** Não considerar multiplayer v0.8 finalizado.

## Escolhas 101–116 aprovadas pelo usuário em 2026-10-14

| Questão | Resposta | Consequência |
|---|---|---|
| 101 | B | Lembrar o último perfil, possibilitando trocar quando quiser. |
| 102 | B | Perfis locais agora, login remoto **opcional futuro**. LAN sem conta obrigatória continua válido. |
| 103 | B | Não mostrar CMD normalmente; diagnóstico opcional exibe console. |
| 104 | B | Zoom inteiro calculado a partir do espaço disponível no monitor. |
| 105 | C | Janela e tela cheia sem bordas; alternar com F11 ou Alt+Enter. |
| 106 | C | Região preta vista durante o jogo ainda requer investigação: não assumir causa sem reprodução e gravação. |
| 107 | B | Launcher minimiza ao iniciar, observa o processo, retorna ao encerrar. |
| 108 | B | Diagnóstico com logs e recuperação de backups de maneira explícita, não auto-restore. |
| 109 | C | Objetivo de distribuição: **ZIP portátil e instalador completo**. Instalador ainda pendente nesta entrega. |
| 110 | C | Efeitos opcionais somente quando não sacrificarem a taxa de quadros. Ainda não adicionados. |
| 111 | C | Launcher/saves e servidor/lobby por etapas com QA. |
| 112 | A | Quando pronto, administrar servidor dedicado no próprio launcher. Botão desabilitado por enquanto. |
| 113 | B | Convites de trocas/batalhas discretos com aceitar/recusar; futuro. |
| 114 | C | Atalho configurável para painel multiplayer no jogo; futuro. |
| 115 | A | Windows primeiro, Android depois. |
| 116 | A | Validar dois jogadores no dedicado, depois 3 e 4. |

## Alterações implementadas neste incremento

- `tools/emerald_launcher.py`: última conta/perfil é salva num pequeno arquivo `launcher-settings.json` **fora do arquivo .sav** (padrão em `%LOCALAPPDATA%/EmeraldHybrid/`; modo portátil ao lado da pasta de perfis). Salva também diagnóstico (checkbox), último IPv4 e porta. Escrita via arquivo temporário e `os.replace`, com tamanho de leitura limitado.
- Execução Windows normal usa `CREATE_NO_WINDOW`, descartando o spam de `ReadFlash` no stdout sem gerar logs gigantes, e salva stderr em `logs/jogo-<data>-<id>.log`. O canal LAN usa arquivo próprio via `--lan-log` na pasta logs. Modo opcional de diagnóstico usa `CREATE_NEW_CONSOLE` e mostra CMD **sob demanda**. Iniciar `pokeemerald.exe` diretamente ainda exibirá console; a experiência sem CMD exige abrir pelo launcher.
- Launcher minimiza durante o jogo; acompanha saída via `Popen.poll()` e `tk.after` sem bloquear interface e se restaura ao encerrar. Em erro de saída, avisa e orienta habilitar diagnóstico. Evita abrir segunda instância do mesmo launcher com processo ainda ativo.
- Ações de **backup manual** e **recuperação explícita** de um backup numerado, somente quando não houver partida sob controle do launcher. Usam `emerald_profilectl.exe` e locks/segurança já existentes. Não tocam `.sav` sem confirmação de recuperação. Arquivos de backups são `000001.sav` etc. O validador nativo ainda é apenas **estrutural**, não checksum completo; não prometer recuperação garantida nem acionar auto-restore.
- `src/platform/sdl2.c`: em desktop, lê `SDL_GetDisplayUsableBounds(0)` e calcula escala inteira inicial; mantido `SDL_RenderSetIntegerScale(SDL_TRUE)` e filtro nearest. F11/Alt+Enter alternam fullscreen-desktop e janela. Com `__ANDROID__` definido, caminho da nova escala/atalho é compilado fora, preservando orientação/controle Android atuais.
- `scripts/verify_v080_profile_patch.py` mantém auditoria histórica: remove **somente blocos de vídeo revisados, exatos**, antes de comparar o hash do SDL original; alterações não autorizadas continuam falhando a auditoria.
- `tests/test_emerald_launcher.py` ganhou casos de preferências persistentes, tratamento de configurações corrompidas e não alteração de bytes de save de laboratório.

## Segurança, compatibilidade e limites

- **Nunca** recuperar backup enquanto o jogo está aberto. O gerenciador CLI pode ter validação parcial: manter cópia do .sav real fora do aplicativo.
- Recuperar o perfil selecionado não muda Trainer ID; contas atuais são locais, não autenticação em servidor.
- Os dois slots LAN atuais continuam P2P e o host precisa jogar. Servidor dedicado, lobby, quatro jogadores, login online e Android launcher novo **não existem nesta etapa**.
- Otimização para 60 FPS é objetivo; não afirmar medição de performance sem testes em hardware. Comportamento turbo e áudio não alterados.
- Escalamento inteiro pode deixar margens pretas normais em fullscreen; **isso é diferente da região preta reportada pelo usuário no conteúdo do jogo**, que ainda precisa de QA com imagem/etapa/reprodução.
- O fechamento seguro de `AgbMain`/flush precisa de revisão, assim como checksums do `.sav`, antes de backup automático depois de cada save manual (#79A já decidido).
- A restauração do processo do jogo não tem gerenciamento de crash avançado no sistema operacional; o launcher detecta código de saída e oferece logs.
- Decisão #109C de instalador + ZIP **não implementada integralmente**, pois ainda precisa de packaging, assinatura/segurança e testes de desinstalação sem apagar saves.

## QA obrigatório / evidência

1. Testes unitários do launcher pelo GitHub Actions, builds Windows e Android da revisão com hash do SDL auditado. **Consultar status de execução por SHA, não confiar neste documento como certificado.**
2. Teste Windows de abertura de jogo sem console, jogo em janela zoom maior e F11/Alt+Enter, toggle de diagnóstico, alternar perfis.
3. Carregar, salvar, encerrar e reabrir dois perfis autênticos distintos; verificar que o jogo e o CLI usam o mesmo arquivo, sem conflito de lock.
4. Backup com save completo, restaurar backup selecionado e verificar a recuperação. Testar arquivo corrompido com cópia, nunca único save pessoal.
5. LAN dos dois jogadores, entrada por IP e Cable Club/trocas; sem regressões e sem falsificar tempo real.
6. Investigação da zona preta (questão 106C), com captura reproduzível de corte de sprites/menu/viewport, sem supor causa.

## Continuidade e rollback

- Branch: `feature/lan-v080-mega-desktop-polish`; PR #9 em rascunho.
- Origem: `feature/lan-v080-desktop-graphical-launcher` (PR #8) e base M0/M1 (PR #6).
- **Rollback comprovado pelo usuário:** `feature/lan-v0721-viewport-culling` SHA `a87e2c49e453db32def5e71ba2a2e696a911d504`.
- O atual incremento não altera batalhas, mapas, scripts de quests ou saves original. Testar sempre em diretório separado com backups.
- Próximos incrementos: checksum completo / fechamento seguro / backup após save, instalador verificado, correções de viewport reais; **depois** SessionServer headless e lobby para 2 antes de 3/4 e Android.
- **A cada atualização** atualizar `AI_README.md`, este relatório e PR com commit SHA, adicionados/alterados/removidos, testes e riscos.
