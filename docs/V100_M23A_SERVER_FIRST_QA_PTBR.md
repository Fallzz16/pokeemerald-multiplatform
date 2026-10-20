# Emerald Hybrid v1.0 — M2.3-A: iniciar servidor sem abrir o jogo

**Correção para o fluxo do Laboratório no Windows.** Mantém a M2.2-B
validada (5/5 testes pelo usuário) e a M2.3 de início manual.

## Problema confirmado
Na M2.3 anterior, `ABRIR 2 JOGOS (NOVO)` iniciava servidor e **ambos os
jogos** na mesma operação. O Lobby aberto antes não tinha sala ativa,
mostrando `SEM SESSÃO EHL8`, `SERVIDOR DESLIGADO` e controles desabilitados.
O botão `ENCERRAR SALA` respondia que não existia servidor local ativo.
A captura de tela enviada pelo usuário comprova essa limitação de UX.

## Correção
- Novo botão `INICIAR SERVIDOR (SEM ABRIR JOGO)`, disponível apenas em
  `EHL8 local`. Selecionar saves de teste ANTES de clicar: nesse ponto
  o Laboratório **importa cópias isoladas dos saves**, mas não abre jogos.
- O Lab inicia um único servidor em `127.0.0.1`, mantém o processo e
  o PIN apenas em memória e disponibiliza o Lobby **0/2**, **PRONTOS 0/2**
  e **PARTIDA INICIADA NÃO**.
- Ao pressionar `ABRIR 2 JOGOS (NOVO)`, o Lab detecta seu próprio
  servidor ainda aberto e usa a MESMA sessão de QA e a MESMA porta/PIN.
  Não inicia outro servidor, não cria outros perfis nem apaga os saves.
- Se a porta/PIN tiver mudado, bloqueia a entrada e explica o motivo.
- `INICIAR SALA` no Lobby permanece desabilitado até haver 2/2 READY.
  Ao clicar, envia START pelo canal administrativo privado, iniciando o
  jogo, enquanto os jogadores enviam READY automaticamente.
- `CONTINUAR SOZINHO`, backups pós-jogo, simular queda, KICK, LOCK,
  bot tests e correção de cores dos personagens foram preservados.

## Instalar
1. Feche jogos e Laboratório anteriores. Preserve a pasta M2.2-B/M2.3
   que já funciona, sem sobrepor seus arquivos.
2. Baixe o ZIP **M2.3-A completo** do CI e extraia o ZIP interno em
   uma pasta NOVA, com o jogo, SDL2.dll, Lab e servidor correspondente.
3. Abra `EmeraldQALab.exe` e selecione `EHL8 local (2 jogadores)`.
4. Escolha cópias de saves ou deixe os campos vazios se quiser dois
   saves de teste novos. **Os saves ficam isolados do launcher original.**
5. Clique `INICIAR SERVIDOR (SEM ABRIR JOGO)`.
6. Abra `LOBBY AO VIVO` e confira `SALA 0/2`,
   `SERVIDOR ATIVO (localhost)`, `PRONTOS 0/2`,
   `PARTIDA INICIADA NÃO`. Nenhuma janela do jogo deve ter aberto.
7. No Laboratório, clique `ABRIR 2 JOGOS (NOVO)`. Verifique que
   aparecem apenas duas janelas de jogo e que o Lobby passa para
   `2/2 PRONTOS` e ainda `PARTIDA INICIADA NÃO`.
8. Aguarde **30 segundos** sem clicar START; os jogos devem
   permanecer conectados e aguardando o anfitrião.
9. Clique `INICIAR SALA (2/2 PRONTOS)`; os dois entram no jogo.
10. Teste `SIMULAR QUEDA QA_B`, depois QA_A. Cada um deve
    reconectar automaticamente. `REMOVER QA_B` deve expulsar sem
    reconexão. Confirme sprites e saves.
11. Feche jogos normalmente; reabra cada conta com
    `CONTINUAR SOZINHO`. Confirme Pokémon, itens e localização.

## Relatórios
Se qualquer teste falhar, envie print do Lobby e `servidor.log`,
`QA_A-rede.log`, `QA_B-rede.log` da sessão do Laboratório. O
PIN e os saves reais não precisam ser enviados.

## Limitações
- Não inicia servidor público dedicado independente do Laboratório;
  esta ferramenta controla somente o servidor local dela.
- `INICIAR SERVIDOR` prepara saves de teste (cópias), embora
  não abra o executável de jogo.
- A sala usa a rede local `127.0.0.1`, sem WAN aberta.
- Um servidor vazio encerra após o período ocioso configurado (15 min).
- **QA humana M2.3-A ainda pendente** até você confirmar.
- Rollback: use a versão M2.2-B do commit `5e53e40`.

## Entrada individual (correção posterior à M2.3-A)

Após INICIAR SERVIDOR (SEM JOGO), use **ENTRAR QA_A** e depois **ENTRAR QA_B** para conectar um jogador por vez. Cada botão lança apenas a respectiva conta já preparada, sem novo servidor, sem novo save e sem nova importação. ABRIR 2 JOGOS continua disponível: inicia ambas caso nenhuma esteja aberta, ou somente a conta que falta. **REABRIR 1 CONTA é exclusivamente para CONTINUAR SOZINHO offline depois que a sessão anterior terminar**. Não use esse controle para entrar na sala EHL8.

Testar: 0/2 sem jogo; ENTRAR QA_A => 1/2; ENTRAR QA_B => 2/2; 30 s sem START; START manual; KICK/reconexão e integridade dos saves. Também testar uma segunda sala com ENTRAR QA_B seguido de ABRIR 2 JOGOS, que deve acrescentar apenas QA_A. Testes automatizados não equivalem a aprovação Windows real.

## Correção M2.3-B2 — reentrada e liberação de porta

Teste adicional no Windows: inicie servidor 0/2, entre QA_A (abre uma instância de jogo), feche QA_A normalmente, reabra QA_A na mesma sala (não deve criar servidor/saves novos), entre QA_B e verifique 2/2; espere 30 segundos sem START e inicie pelo anfitrião; verifique sprites, quedas, KICK e saves. Depois use PARAR TESTES, aguarde saída de todos os processos pertencentes ao Lab, e inicie nova sala na MESMA porta 45680. Caso a porta permaneça ocupada, verifique com `netstat -ano | findstr :45680`; não finalize processos desconhecidos. O botão ENTRAR QA é entrada no cliente de jogo, não comando READY headless. QA humano e CI desta revisão ainda pendentes.


## M2.3-B2 Windows Preview — roteiro obrigatório da próxima build

**Atenção:** verifique `REVISAO_EXATA.txt` no ZIP e compare com o commit exibido no GitHub Actions. Extraia o ZIP inteiro em uma pasta NOVA; NÃO copie executáveis individualmente, NÃO substitua versão funcional e NÃO utilize saves pessoais sem backup. O pacote deve conter `pokeemerald.exe`, `SDL2.dll`, `EmeraldQALab.exe`, `EmeraldSessionServerM22.exe`, `EmeraldSessionServerM23.exe`, `emerald_profilectl.exe` e `SHA256_COMPONENTES.txt`.

1. Execute `ABRIR_LABORATORIO.bat`, selecione EHL8 local, porta 45680, PIN de 6 dígitos, perfis isolados QA_A / QA_B.
2. INICIAR SERVIDOR (SEM JOGO): confira nenhum jogo aberto, lobby 0/2 e servidor ativo.
3. ENTRAR QA_A: confira apenas um pokeemerald.exe; feche QA_A e clique ENTRAR QA_A outra vez. A sessão/porta/saves devem permanecer os mesmos.
4. ENTRAR QA_B: confira lobby 2/2, PRONTOS 2/2; aguarde 30s sem início automático.
5. Clique INICIAR SALA, movimente A e B, observe se sprites, mapas e câmera funcionam.
6. Feche ambos os jogos **sem fechar servidor**, clique ABRIR 2 JOGOS (NOVO) e confira apenas duas novas janelas usando mesma sessão e servidor.
7. Simule queda A, depois B; verifique reconexão em até 60s. REMOVER QA_B deve impedir reentrada automática do removido.
8. PARAR TESTES, aguarde os processos fecharem. Inicie servidor novo **na mesma porta 45680**; não deve dizer ocupada por processo desta versão.
9. Teste salvar/CONTINUAR SOZINHO para cada treinador e compare o save original com backup; nenhuma modificação direta em saves fonte.

**Se falhar:** guarde `servidor.log`, `QA_A-rede.log`, `QA_B-rede.log` e `report.json` no diretório da sessão, além do print e commit em `REVISAO_EXATA.txt`. Não compartilhe PIN ou seus saves privados. O Auto QA não substitui esses testes gráficos de gameplay.


## Correção M3.0 — Jogo abre, mas controles aguardam START (2026-10-20)

**Bug real relatado pelo usuário:** ao pressionar **ENTRAR QA_A**, uma janela `pokeemerald.exe` era aberta e o usuário conseguia **carregar um save e andar pelo mapa** antes de conectar QA_B ou pressionar `INICIAR SALA`. O servidor já aguardava START, mas essa espera não controlava os botões locais do Emerald; portanto os testes do protocolo não a detectavam.

**Comportamento esperado com a nova build desta branch:**

1. O servidor iniciado pelo Lab permanece em 0/2, sem jogo aberto.
2. Ao clicar ENTRAR QA_A, **uma janela do Emerald ainda deve abrir imediatamente**, pois o jogo precisa executar frames para o cliente EHL8 receber JOIN/READY/START. Agora, contudo, **o teclado e o gamepad não permitem começar/andar/selecionar saves enquanto a sala espera**. O título da janela indica que está aguardando segundo jogador e START.
3. O Lab atualiza 1/2. ENTRAR QA_B abre uma segunda janela também aguardando; a sala chega a 2/2, PRONTOS 2/2, PARTIDA INICIADA NÃO.
4. Aguarde ao menos 30 segundos: ambos devem permanecer incapazes de entrar na campanha pela interface do jogo. O servidor deve permanecer ativo, sem timeouts artificiais.
5. Clique **INICIAR SALA (2/2 PRONTOS)** no Lobby. O servidor envia START aos dois. **Só então** o teclado e gamepad são liberados, sem reiniciar o jogo, recriar saves ou fechar/reabrir a conexão.
6. Caso EHL8 falhe ANTES de START, controles continuam bloqueados para não apresentar jogo local como multiplayer sem aviso, e o título mostra falha; feche a janela e use o diagnóstico/backup do QA Lab.
7. Caso a conexão caia DEPOIS do START, o port NÃO re-bloqueia os controles: o progresso solo continua localmente (sem presumir presença online). Feche normalmente e reabra solo para conferir save.
8. O modo `offline`, Cable Club legado P2P e o resto do jogo **não passam pela espera**, pois o switch `--session-wait-for-start` só é usado nas execuções dedicadas EHL8 que optam pela espera.

**Detalhe técnico:** isto é inicialmente um **bloqueio de entradas do jogo**, não um congelamento completo de todas as simulações internas (áudio, scripts ou relógio). O motor, o render e a conexão EHL8 precisam continuar avançando para receber START. Não prometer pausa integral de gameplay/timeplay até que seja implementada e medida sem bloquear o cliente TCP.

**Testes:** casos de regressão na camada Python para os comandos QA e launcher, `tests/test_ehl8_start_gate.c` para transições de desbloqueio/falha e build real Windows/CI. **QA humano desta versão ainda é obrigatório** para comprovar tela e controles com duas instâncias.
