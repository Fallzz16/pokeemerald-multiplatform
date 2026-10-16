# Emerald Hybrid v1.0 — M2.3 Lobby com início pelo anfitrião

**Prévia experimental. Preservar M2.2-B em outra pasta. Não alterar saves originais.**

## Situação
- M2.2-B: 5/5 testes humanos aprovados: conexão 2/2, reconexão automática de QA_B e QA_A, remoção administrativa definitiva e saves individuais.
- M2.3: os jogadores continuam enviando READY automaticamente ao se conectarem.
  **A única novidade manual nesta etapa é o INICIAR SALA pelo anfitrião.**
  Botão pessoal de Pronto/Aguardar será outro incremento.
- Modo novo é opcional (`--host-start --resume-v1 --admin-stdin`); builds
  antigos sem o marcador SHA256 mantêm início automático como antes.
- O botão START só fica habilitado com **2/2 participantes prontos** e
  sessão ainda não iniciada. O servidor recusa START com 0, 1 ou 2 jogadores
  ainda não prontos. A confirmação nunca é simulada pela interface.
- Depois de START a movimentação e reconexão são as mesmas da M2.2-B.

## Instalar
1. Feche todas as janelas do Emerald e do Laboratório.
2. Baixe **o pacote M2.3 COMPLETO**, extraia o ZIP interno em uma pasta
   **totalmente nova**. Não copie apenas `EmeraldQALab.exe` ou
   `EmeraldSessionServerM23.exe` para uma instalação M2.2-B.
3. Confirme que nessa nova pasta aparecem `pokeemerald.exe`,
   `SDL2.dll`, `emerald_profilectl.exe`, `EmeraldQALab.exe`,
   `EmeraldSessionServerM23.exe`, `EHL8_M23_GAME_MATCHED.txt`.
4. Duplo clique `EmeraldQALab.exe`; selecione **EHL8 local**.
   Use duas cópias dos saves ou saves de teste e clique **ABRIR 2 JOGOS (NOVO)**.

## O que testar (obrigatórios)
1. **Sala aguardando host:** abra `LOBBY AO VIVO` com dois jogos abertos.
   Esperado: **SALA 2/2**, **PRONTOS 2/2**, **PARTIDA INICIADA NÃO**;
   **INICIAR SALA (2/2 PRONTOS)** habilitado. O jogo aguarda, sem iniciar sozinho.
2. **Iniciar manualmente:** clique em `INICIAR SALA (2/2 PRONTOS)`,
   confirme. Esperado: os dois jogos entram em **EM JOGO**,
   **PARTIDA INICIADA SIM**, ambos se enxergam e caminham.
3. **Reconexão:** clique `SIMULAR QUEDA QA_B`, observe
   **RECONECTANDO**, reserva da vaga, retorno a **2/2**. Repita com QA_A.
4. **Controle admin:** clique `REMOVER QA_B`. Esperado: QA_B **não**
   reconecta sozinho; QA_A continua jogando.
5. **Saves:** salve nas duas partidas, feche e reabra individualmente por
   `CONTINUAR SOZINHO`. Verifique Pokémon, itens, progresso e localização.
6. **Sprites:** Brendan e May devem manter cores corretas nas quatro direções,
   após warps e durante reconexão. Se houver mudança, envie print.
7. **Opcional:** simule 50 identidades em lotes. Esperado 25/25.

**Atenção:** os jogos ainda enviam READY automaticamente, mas o servidor
não libera START até o anfitrião autorizar. O botão só controla o início da
**primeira** sessão, não interrompe partidas já iniciadas. Com um jogador
desconectado após START, o outro pode continuar, conforme escolha 45A.

## Relatórios
Pelo Lobby, clique `Abrir logs`: envie `servidor.log`,
`QA_A-rede.log`, `QA_B-rede.log` e `report.json`, conforme o erro.
Ocultar dados privados e nunca enviar saves ou PIN. Se o botão não habilitar,
enviar print da sala e do indicador PRONTOS.

**QA real ainda necessária**: o sucesso do CI não valida interações no
Windows do jogador. LAN/VPN privada; não expor o PIN em rede pública.

**Rollback**: feche a pasta nova e continue usando o pacote M2.2-B
(commit `5e53e40`) aprovado por você.
