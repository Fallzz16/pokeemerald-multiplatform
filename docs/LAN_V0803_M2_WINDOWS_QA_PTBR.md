# Emerald Hybrid EHL8 — Guia de teste da MEGA atualização M2 (Windows)

**Versão de QA experimental. Não substitui o Emerald Hybrid v0.8.2 instalado e confirmado pelo usuário.** Nesta etapa, o servidor independente retransmite posições dos treinadores em Hoenn. **Batalhas e trocas continuam usando o modo LAN P2P anterior e não estão integradas ao servidor EHL8.**

## Como testar com 3 dispositivos (ou 2 PCs com o servidor em um deles)

1. Faça backup externo dos seus saves atuais. O instalador EHL8 Preview tem **pasta de instalação própria** e perfis separados em `%LOCALAPPDATA%\EmeraldHybridEHL8Preview\profiles`; **não** substitui os perfis de `%LOCALAPPDATA%\EmeraldHybrid\profiles`. Se usar ZIP portátil em vez de instalador, os perfis ficam na subpasta `profiles` da extração.
2. Instale a edição **EHL8 PREVIEW** pelo novo instalador Windows do GitHub ou extraia **o ZIP portátil completo em uma pasta nova**. Não execute só `EmeraldLauncher.exe` separado, ele precisa de `pokeemerald.exe`, `SDL2.dll`, `emerald_profilectl.exe` e `EmeraldSessionServer.exe` lado a lado.
3. No computador que será o servidor, abra `EmeraldLauncher.exe`, defina porta `45680`, PIN **exatamente 6 dígitos** e clique **Iniciar servidor dedicado**. O processo do servidor fica separado do jogo, ocultando CMD. Se o botão não encontrar `EmeraldSessionServer.exe`, o pacote está incompleto. Confira a pasta de logs.
4. No primeiro PC jogador, abra o launcher, crie novo perfil local ou **importe uma CÓPIA** do próprio `.sav`, sem compartilhar o save entre jogadores. Escolha a porta `45680`, informe o IPv4 privado do PC servidor, coloque o mesmo PIN e marque **Entrar via servidor dedicado EHL8**. Clique **Jogar com amigos**. Se o servidor estiver no **mesmo launcher**, o IP pode ficar vazio para usar `127.0.0.1`.
5. No segundo PC jogador, faça o mesmo com **outro perfil** e o IPv4 do servidor. Após os dois estarem conectados, o servidor envia START. Jogue normalmente até ambos acessarem a mesma cidade/rota e aproximarem as câmeras.
6. Teste andar, correr, entrar/sair de prédio, trocar mapas, esconder o avatar do amigo quando fora da tela, voltar à câmera e abrir menus. O personagem remoto é um sprite virtual sem colisão, não altera a história individual.
7. Feche as duas partidas e abra novamente cada perfil **offline**, verificando treinador, equipe e progresso; crie backups e compare com as cópias externas. Teste também fechar abruptamente o servidor para verificar que os personagens remotos somem sem travar o Emerald. **Não testar trocas reais valiosas pela nova sessão nesta etapa**, pois o proxy de Cable Club ainda não existe.
8. Para analisar falhas, abra **Abrir pasta de logs** no launcher e procure `cliente-ehl8.log`, `servidor-AAAA...log` e `jogo-*.log`. Antes de compartilhar, remova IPs internos, nomes locais e quaisquer informações pessoais.

## Regras importantes

- **LAN privada/VPN confiável apenas.** A versão EHL8 usa PIN simples, sem TLS/autenticação forte. Não faça encaminhamento de portas do roteador, não use DMZ e não exponha a porta ao público.
- Neste modo EHL8 existe **um único TCP 45680** entre cada jogo e o servidor. O P2P antigo, em contraste, usa TCP 45680 + 45681. Não executar os dois hosts ao mesmo tempo nas mesmas portas.
- Quando o jogo demora a abrir, o cliente começa contar os 12 segundos de conexão só a partir do **primeiro polling de rede**, evitando expirar na intro.
- A função **Hospedar e jogar** ainda inicia o *P2P Cable Club antigo* (independente do dedicado). Para jogar também na máquina que hospeda o servidor, clique no modo EHL8 com IP `127.0.0.1`.
- No launcher, o PIN só é enviado por **stdin local**, não fica guardado no arquivo de preferências nem é mostrado na lista de argumentos do processo. Mesmo assim, o protocolo EHL8 na rede **não criptografa** os dados.
- Se o launcher fechar enquanto hospeda, ele pede confirmação e encerra o processo de servidor. Os `.sav` não ficam no servidor; não são afetados.
- **Dois jogadores** é o limite nesta etapa. O objetivo de quatro continua planejado; não exceder dois no servidor atual.
- A interface agora mostra **o número real de participantes (0/2, 1/2, 2/2)** lendo somente um trecho limitado do log do servidor. A lista de nomes, convites, kick/admin, reconexão 60s, QR e Android launcher moderno ainda são pendências.

## Aceite exigido para promover a versão

- [ ] Jogo abre sem CMD normalmente e não bloqueia quando segundo jogador chega.
- [ ] Dois saves *reais mas copiados* são preservados sem mistura de identidade.
- [ ] Dois avatares remotos se mostram no mapa de ambos os jogadores; movimento, câmera e culling corretos.
- [ ] Warp/mapas/menus funcionam e presença some/retorna corretamente.
- [ ] Desconexão e fechamento do servidor não travam o loop nem corrompem saves.
- [ ] Ambos conseguem salvar, fechar e reabrir offline com progresso íntegro.
- [ ] LAN Cable Club antigo continua normal em modo P2P.
- [ ] Compilação Windows e suíte EHL8/P2P antiga aprovadas no *mesmo SHA*; APK antigo não deve piorar.
- [ ] Regressões e prints/logs revisados; só então recomendar mesclar para branch estável.

## Readmes e rollback

Leia `AI_README.md`, `AGENTS.md` e `docs/LAN_V0803_DEDICATED_SESSION_CORE.md` para continuar este desenvolvimento. Se o teste falhar, não altere a instalação v0.8.2; volte a ela e preserve as cópias externas dos saves. Base do M2: `feature/lan-v080-mega-desktop-polish`. O rollback LAN antigo comprovado pelo usuário: `feature/lan-v0721-viewport-culling` commit `a87e2c49e453db32def5e71ba2a2e696a911d504`.

**QA automatizado de sockets não equivale a QA visual no jogo**; registrar feedback real do usuário antes de classificar como lançamento final.


## Testes novos da retomada (não ignorar)

- **Entrada tardia:** inicie EHL8 com duas pessoas, aguarde os personagens aparecerem, feche um dos jogos, espere a sala mostrar `1/2` e entre com outro perfil no slot disponível. O novo jogo deve permanecer conectado; não pode cair por READY duplicado. A segunda pessoa precisa ver as poses do recém-entrado. Esta correção **não** reserva uma vaga para o mesmo usuário por 60 segundos; essa exigência permanece planejada.
- **Contador real do launcher:** antes de alguém entrar, observar `0/2`; ao entrar uma pessoa, `1/2`; duas, `2/2`; após alguém sair, `1/2`. Se os logs ainda não estiverem disponíveis, o launcher informa aguardo em vez de inventar uma contagem.
- **Empacotamento por commit:** nova distribuição exige que `pokeemerald.exe`, `EmeraldLauncher.exe`, `EmeraldSessionServer.exe` e `emerald_profilectl.exe` tenham sido compilados e aprovados **no mesmo SHA de origem do pacote**. O arquivo `SHA256_COMPONENTES.txt` na distribuição apresenta os hashes. Nunca entregue o artefato de um workflow antigo como se contivesse a correção atual. A versão experimentada pelo usuário v0.8.2 é uma instalação distinta.


## Teste da extensão de reconexão automática (M2/4, PR #13)

**Importante:** a seção histórica de entrada tardia acima descreve a versão anterior. Nesta versão experimental, **um jogador que caiu sem encerrar voluntariamente reserva sua vaga durante até 60 segundos**, e outro perfil não pode tomá-la sem a credencial secreta de recuperação.

**Faça estes testes apenas após o pacote CI desta branch ter sido aprovado, em pasta/instalação separada, usando dois saves COPIADOS e diferentes.**

1. Inicie o servidor pelo launcher em um PC e conecte dois jogos Emerald em LAN/VPN privada, com o mesmo PIN da sala. Aguarde `2/2`, START e sprites no mapa de ambos.
2. Desconecte por 5 a 10 segundos **somente a rede de um cliente**, sem fechar o executável do jogo nem o servidor. O outro jogador deve continuar podendo se mover normalmente e observar o personagem desconectado desaparecer.
3. Restaure a rede antes do limite de 60 segundos (o cliente pode precisar de alguns segundos para detectar a queda TCP). O cliente deve autenticar-se novamente com o token em memória, recuperar o mesmo slot e reaparecer após enviar poses. Não deve solicitar novo perfil/save.
4. Experimente ligar um terceiro cliente com outro perfil durante a reserva. A sala de dois slots não deve deixá-lo roubar a vaga reservada. Isso protege a posição, **não prova anti-cheat nem login online**.
5. Repita com falha superior a 60s. A expectativa é o cliente encerrar tentativas e liberar a reserva no servidor ao expirar. Ele não deve travar, entrar em loop infinito ou apagar o save.
6. **Sala aguardando outro jogador:** abra apenas o primeiro cliente, aguarde mais de 35 segundos e confirme que a conexão continua ativa graças ao HEARTBEAT. Outro jogador deve conseguir entrar depois para iniciar a sessão.
7. Volte ao jogo **offline e P2P antigo** para verificar que Cable Club, saving, diálogos rápidos, áudio e Quest UI não sofreram regressões. Faça backup e feche corretamente.

**Limitações desta versão:** o cliente mantém a credencial apenas em RAM — fechar o Emerald definitivamente encerra sua capacidade de retomada. O servidor continua sendo um beta **somente de exploração/presença**, sem repassar batalhas/trocas pelo EHL8, nem autenticação WAN. Jamais abrir TCP do EHL8 no roteador público. Não reportar QA de dois Emeralds como executado pela equipe até o usuário confirmar com prints/logs.
