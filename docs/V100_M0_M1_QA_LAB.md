# Emerald Hybrid v1.0 — M0/M1: Laboratório de duas contas (Windows)

**ESTADO:** primeira entrega de desenvolvimento para teste. NÃO é a release v1.0 pronta. O servidor EHL8 permanece uma preview de dois jogadores, e a renderização de dois Emeralds reais ainda requer validação no PC do usuário.

## O que o Laboratório faz

- Aplicativo gráfico Windows `EmeraldQALab.exe`, independente do launcher principal, sem CMD no fluxo normal.
- Abre **duas instâncias reais** do `pokeemerald.exe` com perfis `QA_A` e `QA_B` em um diretório novo e isolado para cada execução.
- Importa **cópias** opcionais de um `.sav` real por jogador usando o `emerald_profilectl.exe` já existente, com verificação SHA256 de origem/destino; se o campo estiver vazio, cria flash apagada para **New Game** (não cria saves de jogo falsos/manipulados).
- Modo **EHL8 local**: inicia `EmeraldSessionServer.exe` em `127.0.0.1`, porta configurável, com 2 slots e PIN enviado via stdin. Os dois jogos recebem `--session-client` e `--session-pin-stdin` (PIN não entra nos argumentos).
- Modo **Offline**: abre dois jogos independentes sem rede para testar o isolamento de perfis.
- Gera logs por jogador, relatório de exit codes e chama `emerald_profilectl backup` somente depois de ambos os jogos fecharem. Um save ainda em branco não passa na validação do gerenciador e fica sem backup: isso é comportamento esperado, não corrupção.
- Mantém saves e relatórios de teste até o usuário escolher **Limpar sessão** e confirmar. A limpeza verifica caminho, marcador e ausência de links simbólicos antes de atuar apenas na pasta de QA; **nunca** toca nas pastas de perfis do launcher principal.

## Instalar e usar — versão em ZIP adicional

1. Baixe o pacote **Emerald EHL8 M2 Preview completo** (ZIP portátil recomendado para QA), extraia em **pasta nova**, sem substituir o v0.8.2 existente.
2. Baixe o ZIP separado **Emerald_Hybrid_v1_M1_Laboratorio_Windows.zip** das Actions da branch experimental e extraia os arquivos **no mesmo diretório** de `pokeemerald.exe`, `SDL2.dll`, `emerald_profilectl.exe` e `EmeraldSessionServer.exe`.
3. Inicie `EmeraldQALab.exe` ou `ABRIR_LABORATORIO.bat` (o `.bat` é opcional; diretamente pelo `.exe` não abre CMD).
4. Escolha para a conta A e B um `.sav` existente **somente se desejar copiar progresso real**. Deixar os dois campos vazios faz ambos começarem New Game independentes.
5. Selecione **EHL8 local** (duas pessoas conectadas ao servidor do mesmo PC) ou **Offline** (teste de abertura/isolamento sem multiplayer) e clique **ABRIR 2 JOGOS**. Para avaliar presença remota, os dois saves precisam chegar ao mesmo mapa normalmente.
6. Salve manualmente dentro do jogo se desejar e feche **as duas** janelas normalmente. O Lab registra `report.json` e solicita backups nativos dos saves válidos.
7. Se ocorrer erro, use **Abrir pasta** e envie os arquivos de log necessários sem divulgar informações pessoais; o PIN nunca é gravado pelo Laboratório. Para recomeçar, uma nova execução sempre gera uma pasta isolada diferente.
8. **Limpar sessão** remove exclusivamente a sessão de QA selecionada. Atenção: os `.sav` de QA naquela pasta são excluídos; exporte o que desejar antes. Nenhum save de produção é removido.

Diretório padrão: `%LOCALAPPDATA%\EmeraldHybridV1QALab\sessions\<data-id>\` (perfil, logs, `qa-session.json`, `report.json`).

## Critérios de aceitação e pendências

**Passou no desenvolvimento:** testes Python locais do orquestrador, separação de perfis, proteção de origens, argumentos corretos, caminho de limpeza e proibição de backup durante a execução (mockando o gerenciador, sem rodar o jogo). O workflow Windows compila `EmeraldQALab.exe` separadamente e roda os mesmos testes.

**Ainda precisa do PC Windows:** abrir de fato as duas janelas; verificar duas cenas de Hoenn; esperar o servidor EHL8 marcar `2/2`, renderizar cada avatar remoto quando no mesmo mapa e testar ida/volta de menus/warps e fechamento seguro. Também verificar dois saves válidos reabrindo offline, sem mistura. Um teste de sockets não prova esses itens.

**Não está incluído neste marco:** 50 clientes simulados, reconexão de 60 s, batalhas ou convites pelo EHL8, contas online, novo launcher completo ou quatro jogadores. Estes permanecem nos marcos M2–M7.

## Segurança e rollback

- O servidor do Laboratório **escuta apenas em localhost**. Nunca faz port-forward, DMZ ou expõe a LAN/internet. Para testar com dois PCs de verdade, continue usando o launcher experimental M2 e uma VPN/LAN confiável.
- O jogo continua a bloquear simultaneamente o uso do mesmo perfil; `QA_A` e `QA_B` são perfis diferentes.
- `EmeraldQALab.exe` não inclui o jogo, bibliotecas SDL ou ferramentas de perfil. A distribuição em ZIP contém **apenas o laboratório e as instruções** para usar em conjunto com o pacote M2 já existente.
- Nenhum código do jogo (`src/`), launcher existente ou servidor EHL8 foi modificado nesta entrega; nenhum arquivo de save foi incluído.
- O v0.8.2 já aprovado segue em instalação/branch separada. A branch de trabalho é `feature/lan-v0803-dedicated-session-core` (PR #10 draft). Para voltar atrás, simplesmente feche o laboratório e use sua instalação v0.8.2; os perfis existentes não são migrados nem modificados.

## M1.1 — Painel de 50 identidades simuladas (25 rodadas locais)

**Adicionado:** botão `SIMULAR 50 CONTAS` na mesma janela do Laboratório. Ele cria uma sessão isolada de logs/metadados (sem .sav, sem criação de perfil de jogo), inicia `EmeraldSessionServer.exe` vinculado a **127.0.0.1**, e executa `EmeraldQABots.exe` em segundo plano. O PIN vai por **stdin**, jamais pela linha de comando. Não há conexão à Internet, descoberta de IP remoto ou instalação externa durante o uso.

- Simula **25 rodadas de dois clientes TCP EHL8**, totalizando **50 identidades distintas**. Em cada rodada valida HELLO/WELCOME, PIN, JOIN, READY/START, duas retransmissões de pacotes de movimentação LANP, LEAVE e retorno da primeira identidade à sala em andamento. Testa transporte e protocolos; **não renderiza sprites, não abre 50 jogos, não mede FPS e não executa batalhas**.
- O executor restringe o destino a `127.0.0.1` e o máximo a 25 rodadas para evitar ser usado como gerador arbitrário de carga contra terceiros. 50 identidades não significam 50 conexões simultâneas — limite de 2 permanece.
- `bots-report.json` é criado com contagem de rodadas aprovadas/falhadas, durações, latência aproximada de resposta WELCOME e relay, eventos resumidos, erros e a afirmação explícita de teste somente de rede. Não inclui PIN/saves. `logs/clientes-simulados.log` e `logs/servidor-bots.log` ficam na sessão isolada.
- `Parar bots` cancela as execuções. `Limpar teste bots` exige confirmação e remove somente a sessão marcada de bots, se encerrada. O botão `ABRIR 2 JOGOS` mantém o comportamento anterior e não pode ser utilizado enquanto os bots estão rodando.
- A build Windows de QA passa a entregar **dois executáveis** (`EmeraldQALab.exe` e `EmeraldQABots.exe`). Ambos precisam ficar no mesmo diretório de `pokeemerald.exe` e `EmeraldSessionServer.exe`. O teste em fonte Python usa `tools/emerald_qa_bots.py`.

### QA deste incremento

- Testes estáticos do envelope EHL8 (header 28 bytes), LANP de 18 bytes e validação de PIN/identidades.
- Testes de socket loopback com **servidor de teste reduzido**: múltiplas rodadas completas, relay bidirecional, retorno de identidade e falha segura com PIN inválido. Não considerar essa simulação comprovação do servidor de produção.
- Testes do orquestrador: criação e limpeza segura da pasta de bots, nenhum `.sav` criado e PIN não exposto em argumentos.
- Um teste de integração adicional (`RealEHL8ServerTests`) é executado **quando a suite está dentro do repositório completo**, usando diretamente `tools/emerald_session_server.py` de produção. No pacote fonte separado ele registra SKIP; não tratar como PASS.
- Verificações ainda exigidas: workflow Windows empacotar ambos os binários, testar o simulador contra o **servidor verdadeiro**, confirmar no PC Windows com `25/25`, perfis de jogo e renderização, integridade de saves e bugs reportados. **A screenshot enviada pelo usuário mostra o jogo e dois sprites; não comprova sozinha duas instâncias remotas EHL8 nem backup/round-trip.**

### Como usar o botão de bots

1. Instale a atualização do Laboratório na **pasta da EHL8 Preview completa**, substituindo apenas arquivos deste Laboratório; não substitua `pokeemerald.exe`, servidor, biblioteca SDL2 nem saves.
2. Abra `EmeraldQALab.exe`; deixe as instâncias reais do jogo fechadas.
3. Confirme porta local e PIN de seis dígitos. Clique `SIMULAR 50 CONTAS` e aguarde a mensagem do resultado.
4. Para conferir as falhas, use `Abrir pasta` (sessão do jogo) ou acesse `%LOCALAPPDATA%\EmeraldHybridV1QALab\sessions\<ultimo-teste>\bots-report.json` e `logs\clientes-simulados.log`.
5. Se a porta já estiver ocupada por um jogo/servidor, escolha outra porta; não tente reaproveitar a sessão de uma partida real. Bot e sessão de dois jogos não devem executar juntos no mesmo Lab.
