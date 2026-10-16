# EHL8 M2 Palette Fix — QA visual Brendan/May (2026-10-16)

**Status:** correção candidata para testar, NÃO validação visual final.

## Diagnóstico

O usuário testou dois Emeralds conectados ao EHL8 com sucesso; relatou que a
personagem May aparecia com cores/visual alterados na janela de Brendan.
O código de presença transmite corretamente o bit de gênero em LANP (0/1)
e seleciona o graphics ID May/Brendan. Mas `CreateVirtualObject` usa
`PALSLOT_PLAYER`, uma paleta compartilhada com o **personagem local**.
Portanto, quando os gêneros diferem, a sprite remota usa a paleta local e
pode parecer com cabelo/roupas ou acessórios incorretos.

## Solução limitada

- `LanVirtualObjectSetRemotePalette()` aloca uma paleta OBJ **dinâmica** com
  tag exclusiva `0xECF0`, atribuindo seu slot ao avatar remoto.
- A paleta é recarregada na criação e liberada no fechamento/desaparecimento
  do objeto virtual. Não altera a paleta do jogador local, dos NPCs ou os
  arquivos gráficos existentes.
- Se não houver slot livre, a presença remota não será renderizada em vez de
  mostrar cores erradas. O jogo e a rede continuam funcionando.
- Reutiliza o `LoadSpritePalette` e `PatchObjectPalette` do jogo.
- Sem alterações em `.sav`, transporte EHL8, SIO Cable Club, PNG/4bpp,
  mapas, eventos ou sprites do jogador local.
- O `PORTABLE` guard mantém a nova API fora da compilação GBA legada.

## Testes esperados

1. Abrir a preview **nova compilada do mesmo SHA** em uma pasta separada.
   Importar apenas cópias de dois saves reais com Brendan e May.
2. Conectar dois jogadores em EHL8 local (2/2). Colocá-los no mesmo mapa.
   **Na tela de Brendan, May deve usar suas cores corretas**, especialmente
   bandana/roupa/cabelo, nas quatro direções. Verificar Brendan na tela dela.
3. Caminhar, correr, ficar parado, sumir da câmera e reaparecer; entrar e
   sair de casa (forçar warp e recriação de sprite) nos dois jogos.
4. Fechar B e abrir outra sessão limpa; conferir que a paleta é liberada e
   reaplicada, sem mudar as cores dos NPCs nem do jogador local.
5. Salvar ambos, fechar e reabrir offline, conferindo integridade dos saves
   e backups de QA. Testar o Cable Club P2P anterior separadamente.
6. Reportar screenshots comparativos ANTES/DEPOIS e quaisquer efeitos de
   clima/reflexos/animações não corretos.

**QA automatizado:** executar `python -m unittest discover -s tests
-p test_lan_remote_palette_regression.py -v` para guards e call-sites
e a build Windows real por GitHub Actions para verificar compilação.
A suíte estática e o build NÃO comprovam o aspecto visual no PC.

**Rollback:** commit anterior `005de5e36bb189ccae49c08a2abe89fdd7f2297d`,
PR #10 draft. Manter a instalação/ZIP que o usuário testou intacta.
