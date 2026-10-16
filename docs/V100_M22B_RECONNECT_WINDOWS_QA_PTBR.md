# Emerald Hybrid v1.0 M2.2-B — Reconexão nativa (preview experimental)

**Somente Windows. Não substituir versões anteriores e não importar o único save original.**

## O que muda
- `pokeemerald.exe` reconhece token efêmero EHL8 tipo 18. Em caso de queda TCP
  inesperada durante PLAYING, oculta o avatar remoto e tenta retomar a sessão
  durante até 60 segundos com tentativas espaçadas.
- `EmeraldSessionServerM22.exe` reserva a vaga e valida PIN/perfil/token; faz
  rotação do token após retomar. **Kick do administrador é definitivo**.
- `EmeraldQALab.exe` escolhe a reconexão somente quando o pacote completo
  contém `EHL8_M22B_GAME_MATCHED.txt` e os hashes SHA256 do jogo e servidor
  correspondem. Sem o marcador, mantém protocolo anterior.
- Lobby mostra estado RECONECTANDO e vagas reservadas quando informados nos logs.
- Correção de paleta remota May/Brendan (validada pelo usuário) foi mantida.
- Saves independentes, Continuar Sozinho, bots e Cable Club permanecem separados.

## Instalação
1. Feche todo Emerald e Laboratório. **Mantenha a pasta M2.1-B intacta.**
2. Baixe o artefato completo da Action M2.2-B, extraia o ZIP interno em uma
   **pasta nova**; não misture executáveis de outras versões.
3. Abra `EmeraldQALab.exe` pelo duplo clique; se quiser, use
   `ABRIR_LABORATORIO.bat`.
4. Use somente **cópias** dos saves. Selecione EHL8 local e abra duas partidas.

## Testes do usuário — reportar cada resultado
1. **Conexão:** com duas contas no mesmo mapa, verifique sala 2/2 e movimento
   bidirecional, cores corretas de May/Brendan. Resultado esperado: EM JOGO.
2. **Reconexão real no mesmo PC:** com A e B jogando, abra
   `LOBBY AO VIVO` e clique em `SIMULAR QUEDA QA_B` (confirme). O
   servidor fecha somente o socket de QA_B, como uma falha inesperada.
   **Não fecha o jogo nem toca no save.** Esperado: QA_B entra no estado
   `RECONECTANDO (ATÉ 60s)`, uma vaga fica reservada (1/2) e a
   sessão volta a 2/2 / EM JOGO; QA_A nunca congela.
   Repita com `SIMULAR QUEDA QA_A`. Registre print dos estados.
   **Não use REMOVER QA_B para testar reconexão**: um kick do
   administrador é final e intencionalmente não reconecta.
3. **Abandono >60 segundos:** com queda de rede prolongada, a tentativa deve
   encerrar em ERRO DE CONEXÃO, sem fechar o Emerald nem tocar nos saves.
4. **Admin Kick:** remover QA_B deve ser definitivo, **sem religar
   automaticamente**, e QA_A deve seguir jogável.
5. **Saves:** salve nas duas contas, feche as duas e reabra individualmente
   com CONTINUAR SOZINHO. Verifique personagens, itens, localização, cores.
6. **Bônus:** testes SIMULAR 50 CONTAS usam protocolo legado, não a nova
   reconexão, e devem continuar concluindo as 25 rodadas.

## Diagnósticos e limites
- Abra LOBBY AO VIVO e envie print com RECONECTANDO, 1/2, RESERVADA e
  retorno a 2/2 ou ERRO DE CONEXÃO.
- Logs: `%LOCALAPPDATA%\EmeraldHybridV1QALab\sessions\<id>\logs\`
  (QA_A-rede.log, QA_B-rede.log, servidor.log); relatório JSON `report.json`.
- Não publique PIN, saves ou dados pessoais.
- **LAN/VPN privada apenas**: PIN via EHL8 TCP não equivale a TLS.
- Testes C nativos + servidor não substituem os testes visuais de dois jogos
  Windows. Esta versão não inclui batalhas EHL8 ou reconexão de batalhas P2P.
- **Rollback:** feche esta pasta e use novamente sua M2.1-B aprovada; não há
  migração in-place dos saves.
