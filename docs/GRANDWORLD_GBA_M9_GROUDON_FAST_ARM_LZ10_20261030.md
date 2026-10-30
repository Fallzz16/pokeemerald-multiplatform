# Grand World GBA M9 — benchmark ARM LZ10 otimizado x BIOS

**Status: experimento validado no mGBA, mas PR #112 permanece DRAFT.**
Base: PR #110 (contador hardware TM2/TM3), dependente das PRs
#109 (Groudon LZ10 comprovado) e #107/108 (orcamento/duplos).
**A M8 estavel nao foi modificada.**

## Resultado observado — 30/10/2026

[GitHub Actions #41065482122](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41065482122):
**SUCCESS** em dupla compilacao ARM/GBA, 18/18 OWE terrestres visiveis,
12/12 Groudon seguidor com leitura GPU OBJ VRAM, 221 amostras de ciclos
de descompressao via timers GBA 2/3.
[Artefato sem ROM nem saves](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41065482122/artifacts/12983130372).

| Medida (frame original Groudon 64x64, 2048B) | BIOS PR110 | ARM otimizado PR112 |
| --- | ---: | ---: |
| Amostras | 221 | 221 |
| Media de ciclos | 38.626 | **21.549** |
| Pico de ciclos | 39.136 | **21.841** |
| Reduc. media relativa | - | **44,21%** |
| Reduc. absoluta no pico | - | **17.295 ciclos** |
| Parcela do VBlank ocupada pelo pico de UMA chamada | 46,72% | **26,07%** |
| Timer2/3 ocupado (conflitos) | 0 | 0 |
| Pixels originais e animacao Groudon | 9/9 + profiler | **12/12 PASS** |
| Route29 4 OWEs + seguidor + batalha real | 18/18 | **18/18 PASS** |

A ROM ARM final do teste com decoder otimizado tem SHA256
`570cff86069d84e49898c5cb96ed5549fd3906fa88b8c27115d7b8d81b47b06a`.

### Memoria e ROM — nao confundir com o build de producao

O build desta PR adiciona **contadores temporarios para benchmark**.
Comparado ao baseline World ARM sem Groudon comprimido:

- Payload ROM vinculado: **7.360 bytes economizados** mesmo somando
  o custo do decoder ARM no teste;
- EWRAM estatica: **+16 bytes** dos 4 contadores;
- IWRAM estatica: **+552 bytes** do decoder ARM;
- EWRAM livre medida: **27.008 bytes**;
- IWRAM livre medida: **4.120 bytes**, mantendo reserva minima 2.048 B;
- A PR #109, com BIOS, tinha 8.056 bytes de economia ROM real e
  +0 B RAM estatica. Nao atribuir esse valor a PR #112.
- A economia de producao sem os contadores ainda NAO foi medida para
  o decoder otimizado, mas sua tecnica usa os mesmos 6 arrays LZ10.

### Origem / licença

A fonte ASM foi obtida **somente no workspace descartavel de CI** de
`HorstBaerbel/GBA-demo-framework` no commit fixo
`7f5410055d7fafb002ed7536b9cc45274f3a471b`,
arquivo `src/compression/lz77_asm.s`, com cabeçalho MIT preservado.
Rotina original por fleroviux/Cult-of-GBA/BIOS; otimizacao por
Lorenzooone. Codigo upstream **nao foi copiado para esta branch**.
A build pre-processa o assembly com o toolchain ARM real e
liga `LZ77UnCompWrite16bit` na secao IWRAM. Apenas dois calls
de Groudon/diagnostico substituem a chamada do BIOS.

### Por que esta abordagem supera a PR #111

A PR #111 tentou descompressao antecipada em quatro buffers WRAM e
falhou em runtime porque 187/219 pedidos foram feitos dentro do VBlank:
10/12 testes; +8.208B EWRAM sem reduzir o gargalo majoritario.
Esta PR #112 nao depende de staging, mantem uso EWRAM quase inalterado
e reduz diretamente a descompressao que ja ocorre dentro do VBlank.

### Limites obrigatorios para evolucao

- 21.841 ciclos = **26,07% de um VBlank para UMA copia**. Tres chamadas
  com pico consumiriam ~65.523 (78,2%) dos 83.776 ciclos,
  antes de OAM/DMA/audio e outras transferencias. Quatro chamadas
  extrapolariam a janela (projecao, nao stress observado).
- Nao afirmar FPS sustentado, latencia de audio ou hardware fisico
  medidos: os ciclos foram contados pelo mGBA no GBA emulado.
- Nao ativar o decoder genericamente para centenas de especies sem
  validar frames 32x32, simultaneidade, Surf, mapas densos, transicoes,
  saves antigos e orçamento agregado de VBlank.
- O proximo experimento de producao deveria preservar a versao ARM
  apenas se o custo de IWRAM for aceitavel, limitar o numero de
  descompressões comprimidas por frame e observar stutter/copy queues.

**Conclusao:** comparacao A/B ARM com o MESMO LZ10 provou
descompactacao **44,21% mais rapida em media**, sem regressao de pixels
nos 16 samples de VRAM testados nem nos 18 encontros/seguidores.
Manter DRAFT e nunca fazer merge automatico na M8.
