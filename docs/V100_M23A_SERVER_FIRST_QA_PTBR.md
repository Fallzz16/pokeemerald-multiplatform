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
