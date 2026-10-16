# Emerald Hybrid v1.0 — M2.1-B: administração real do lobby

## Alterações
- `LOBBY AO VIVO`: ocupação da sala, jogadores e status de entradas permitidas/bloqueadas.
- `REMOVER QA_A` / `REMOVER QA_B`: remove apenas a conexão de rede daquela identidade.
- `BLOQUEAR ENTRADAS` / `PERMITIR ENTRADAS`: altera a aceitação de novos JOINs;
  não desconecta participantes existentes.
- Novos comandos são enviados por **stdin privado** ao servidor complementar
  `EmeraldSessionServerM21.exe`. Sem listener administrativo; sem dados de .sav.
- O EHL8 anterior `EmeraldSessionServer.exe` é preservado como rollback.
  Sem `M21.exe`, os controles ficam desabilitados.

## Como instalar sem perder os saves
1. Feche o jogo e o laboratório; mantenha sua versão estável inalterada.
2. Extraia o ZIP M2.1-B somente na pasta da preview EHL8 com jogo completo.
   Substitua apenas `EmeraldQALab.exe` e `EmeraldQABots.exe`.
   `EmeraldSessionServerM21.exe` é um arquivo **adicional**, não substitui o anterior.
3. Abra o Lab e escolha EHL8 local; inicie **ABRIR 2 JOGOS (NOVO)**.
4. Abra **LOBBY AO VIVO**. Confirme 2/2 e EM JOGO para as duas contas.
5. Pressione **BLOQUEAR ENTRADAS** e espere BLOQUEADAS; libere e espere PERMITIDAS.
6. Pressione **REMOVER QA_B**. Espere 1/2 no lobby e continue andando com QA_A.
   A janela QA_B pode permanecer aberta, sem conexão EHL8. O save B não é removido.
7. Feche os jogos normalmente. Reabra A e B offline, individualmente, via
   **CONTINUAR SOZINHO**, e confira Pokémon, itens, mapa e backups.
8. Verifique novamente a abertura de duas contas e, com as janelas fechadas,
   execute **SIMULAR 50 CONTAS** (esperado 25/25).

## Limitações
- Administração somente para o servidor local criado pelo Lab, nunca para
  servidores de terceiros. Só funciona com `M21.exe` ao lado do Lab.
- Pronto/Iniciar seguem automáticos. Reconexão autenticada de 60 segundos,
  PvP por convite e lista de salas ainda não estão implementados.
- A rede EHL8 continua limitada a LAN/VPN privada; não exponha a porta na
  Internet pública.
- Validação automática não equivale ao QA visual das duas instâncias no Windows.
  Se algo falhar, envie `servidor.log`, logs da conta e `report.json`.
