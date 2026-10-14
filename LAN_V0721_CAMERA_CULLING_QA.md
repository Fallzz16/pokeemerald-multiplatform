# Emerald Hybrid LAN v0.7.2.1 — Visibilidade inteligente do jogador remoto

**Estado:** implementação experimental em branch isolada. Não confundir aprovação da suíte matemática de viewport com aprovação da renderização no jogo real.

## O que foi implementado

- Retângulo de câmera calculado com os mesmos helpers de projeção do Emerald (`SetSpritePosToOffsetMapCoords`) e a largura/altura real do gráfico do treinador.
- **Renderizar somente quando o corpo do sprite cruza a tela de 240 × 160 pixels:** o teste de interseção usa margem 0 para a visibilidade final.
- Dentro de **32 pixels da área visível**, pré-carregar o sprite, mas mantê-lo invisível até realmente entrar na imagem.
- Se já foi criado, **manter até 48 pixels fora da câmera** para evitar criação/destruição em sequência quando o jogador se aproxima/afasta da borda.
- Fora de 48 pixels, **liberar o sprite remoto e seus recursos gráficos**; o objeto de presença e seus pacotes continuam atualizados pela conexão de rede.
- Fora do mapa atual, ao entrar em batalha ou ao desconectar: continua removendo o sprite, como na v0.7.2.
- Nenhuma alteração no protocolo TCP de presença, Cable Club, salvamento, estrutura do mapa ou NPCs.

## Por que duas margens?

**Pré-carregamento de 32 px:** deixa o sprite preparado antes de entrar em tela; não o desenha.
**Retenção de 48 px:** se ele acabou de sair, mantemos sua alocação enquanto a câmera se move. A diferença de 16 px cria **histerese**, evitando flicker/alocações a cada frame.

Essas margens são em **pixels da câmera**, não em tiles de distância ao jogador. Os sprites têm áreas de desenho diferentes; a checagem considera suas dimensões.

## Como testar

1. Baixar os binários **desta branch**, não da release antiga. Ter dois saves originais independentes, que já funcionaram no jogo. **Não usar os saves artificialmente editados** anteriormente.
2. Abrir host: `pokeemerald.exe --lan-log host.log --lan-host=45680`; cliente no mesmo PC: `pokeemerald.exe --lan-log cliente.log --lan-client=127.0.0.1:45680`.
3. Deixar os dois no mesmo mapa, em posições distantes: o jogador remoto não deve aparecer.
4. Caminhar em direção à área da câmera: o remoto deve aparecer somente quando parte do seu sprite entrar no enquadramento, inclusive nas quatro bordas.
5. Repetir recuando e aproximando na borda diversas vezes: não deve piscar, criar cópias, travar ou sofrer degradação de FPS.
6. Mover a câmera enquanto o remoto permanece parado: o sprite deve entrar/sair de forma correta.
7. Separar os jogadores entre cidade, rota, prédio e Centro Pokémon; confirmar ocultação e reaparecimento no mesmo mapa.
8. Desconectar um cliente, reiniciar sessão e reentrar no mapa; não deve deixar fantasmas gráficos.
9. Entrar no Cable Club, terminar uma batalha e uma troca; verificar regressão e saves.
10. Comparar Windows × Windows, Windows × Android, Android × Android, respeitando o APK armv7 de 32 bits.

## Testes automatizados

```bash
bash scripts/verify_lan_foundation.sh
```

A suíte cobre transporte TCP + serial SIO + snapshots de movimento e **interseção da viewport, bordas exatas e histerese 32/48 px**.

Não testa sprites dentro do mundo renderizado, desempenho real de câmera ou transições de mapa. Para isso, coletar vídeos/capturas dos passos 3–10.

## Próximo incremento (ainda não implementado)

**PokéNav:** ícone de cabeça para Brendan/May indicando o amigo pela localização no mapa regional. Não enviar coordenadas de mapa específicas diretamente a pixels do PokéNav; é necessária uma conversão de mapa para região e offset. A proposta inicial é mostrar a região do amigo, com chave opcional para esconder o marcador.

**Fora do escopo da v0.7.2.1:** setas de direção na tela, sincronização de NPCs, mundo compartilhado completo, colisão entre jogadores e jogadores além dos dois participantes atuais.
