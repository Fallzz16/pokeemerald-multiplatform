# Grand World GBA M9 — Groudon 64x64 LZ10 por frame (PR #109)

**Status: EXPERIMENTAL / DRAFT, NAO MERGE.** M8 estavel intacta.
Dependencias: PR #108 (inventario de bytes reais), PR #107 (VRAM/paletas),
PR #105 (-Os + seções e coleta GC). Engine World fixa:
`15d3888b0d81322a04d3c71b0bce18948761ee44`.

## Execucao real aprovada

[Actions #41057342617](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41057342617),
**COMPLETED SUCCESS**, codigo de implementacao:
`04f0ae68c1889dde3def5ec51ea14a59c8d998f1`.

| Resultado | Valor |
| --- | ---: |
| Groudon normal, frames 64x64 4bpp | 6 |
| Tamanho original no ELF | 12.288 B |
| Frames comprimidos LZ10 alinhados a u32 | 4.152 B |
| Economia bruta antes do codigo extra | 8.136 B |
| **Economia vinculada real de ROM** | **8.056 B** |
| Delta EWRAM estatica (antes - depois) | 0 B |
| Delta IWRAM estatica (antes - depois) | 0 B |
| Identidade byte a byte (cada frame final vs original) | **6/6 PASS** |
| Encontros terrestres reais, follower, batalha e fuga mGBA | **18/18 PASS** |
| Medicao de cycles no VBlank | **NAO realizada** |
| Groudon exibido/animado em tela no mGBA | **NAO testado** |

SHA256 ROM de controle:
`f581ba7e6229732faa17e79a11825682861c67dcbf6ee4670dabff20dd3279ae`.
SHA256 ROM experimental:
`6ca77d46a109d9f36f39b826623167f21e0aee8067b8d8595b39566277898971`.
A ROM continua sendo cartucho de 32 MiB preenchido; 8.056 B de economia
correspondem ao **payload vinculado** e a espaco potencial livre, nao
ao tamanho do arquivo .gba que conserva o preenchimento para o cartucho.

## Como funciona (somente no checkout descartavel da CI)

`tools/grandworld/apply_groudon_frame_lz10.py` extrai os seis frames
reais de `gObjectEventPic_Groudon` no binario ARM baseline usando
`arm-none-eabi-nm -S`, codifica cada um em LZ10, confirma integridade,
gera `grandworld_groudon_frame_lz10.h` com arrays ROM alinhados e troca
a tabela `sPicTable_Groudon` para seis `SpriteFrameImage` com
`.size=2048` e `.relativeFrames=2`.

O motor continua reservando **64 tiles OBJ (2.048 B) por frame**, e a
paleta, animações, shinies, especies e formato de save ficam iguais.
`OW_GFX_COMPRESS` permanece **FALSE**: o motor nao carrega uma folha
inteira de seis frames na OBJ VRAM.
A fila normal de `RequestSpriteFrameImageCopy` reconhece o marcador
de frame comprimido e `ProcessSpriteCopyRequests` usa a chamada BIOS
`LZ77UnCompVram` no destino do frame. Para essa API especifica o encoder
impede backreferences de distancia 1, pois as copias sao em 16 bits.
Nenhum buffer permanente extra em EWRAM e introduzido.

`verify_groudon_frame_lz10.py` le os **arrays ROM vinculados finais**
pelo ELF (nao so o header C de origem), decodifica, compara SHA256 de
todos os seis frames, verifica identidade das duas compilações e
rejeita falta de economia, crescimento estatico de EWRAM/IWRAM ou hash
incorreto. A ROM do candidato compilou realmente para ARM/GBA, nao SDL.

## Limites que impedem o merge de producao

A suite 18/18 usa Route 29: ela comprova nao haver regressao visivel
nesses cenarios, **mas nao desenha o proprio Groudon**. Portanto ainda
faltam: script mGBA de Groudon selvagem ou seguidor realmente visivel,
animacao entre os seis frames, screenshot pixel-perfect, medicao de
ciclos/tempo por frame no VBlank sob varios sprites, e prova de
compatibilidade com saves antigos em transicoes/Surf. Decompressao no
VBlank pode consumir parte do orcamento de cerca de 83.776 ciclos de
VBlank por frame do GBA (GBATEK); isso deve ser medido antes de
liberar para producao.

**Nao aplicar compressao em massa a 1.216 sprites ainda.** O ganho de
8.056 B e real no piloto, mas nao e prova de desempenho nem de
proporcao reproduzivel em outros assets.

Fontes tecnicas:
- https://github.com/gbadev-org/gbadoc/blob/main/content/bios.md
- https://mgba-emu.github.io/gbatek/
