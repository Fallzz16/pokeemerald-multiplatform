# Grand World GBA M9 — diagnóstico gráfico de OBJ VRAM

**Status: experimental, NÃO FAZER MERGE na M8.** A base é a PR #105
(-Os + coleta de seções; áudio original), com a engine World fixada no SHA
15d3888b0d81322a04d3c71b0bce18948761ee44.

## Por que medir antes de recomprimir

O GBA tem 96 KiB de VRAM ao todo, mas a área OBJ nos modos de tiles BG
0-2 possui 32 KiB, equivalentes a 1024 tiles de 4bpp (32 bytes cada).
O mapa de alocação nativo World tem 128 bytes. Contar apenas sprites ativos
e paletas não mede quantos tiles estão ocupados nem a fragmentação.

A compressão de folhas inteiras de overworld continua DESLIGADA:
ela pode ocupar mais OBJ VRAM e atrapalhar Pokémon selvagens simultâneos.

## Implementação isolada

1. graphics_budget_overlay.py: no checkout DESCARTÁVEL da World, expõe o
   mapa de tiles à geração de símbolos do teste mGBA e insere a telemetria
   na CÓPIA do teste Lua. Não modifica o alocador, arte, saves nem fontes
   definitivas. Valida todos os trechos antes de gravar qualquer arquivo.
2. graphics_budget_report.py: confere contagens e calcula ocupação,
   maior bloco contínuo livre e fragmentação com hash SHA256 da ROM.
3. Workflow grandworld-gba-master-rom-sections.yml: ARM/GBA real,
   preserva o perfil -Os+GC da PR #105 e reaproveita a prova mGBA 18/18.
4. Testes unitários específicos para métricas, ausência de amostras,
   dados corrompidos e recusas de patch incompatível.

## Métricas capturadas

- used / free: tiles OBJ ocupados / livres de 1024
- largest_free: maior sequência de tiles livres contíguos
- free_runs: quantidade de segmentos livres separados
- reserved: tiles reservados originalmente pelo motor
- sprites: sprites ativos na pool de 64
- palettes: paletas OBJ ocupadas na pool de 16
- owe: selvagens gerados nos IDs 249 a 252
- follower: seguidor com sprite vivo e visível

Amostras durante a geração, rodízio, batalha e retorno. Este teste **não**
mede FPS, DMA, BG VRAM, compressibilidade, pixels visíveis em tela,
compatibilidade de saves ou economias de bytes. A ROM instrumentada tem
hash diferente da ROM candidata de produção.

## Próximos passos após obter números reais

1. Identificar menor bloco contínuo livre e padrões de fragmentação.
2. Testar reutilização só quando tiles, paleta, forma e frames forem
   visualmente idênticos, preservando shiny e follower.
3. Experimentar compressão SELETIVA em outra branch com comparação A/B
   do uso OBJ VRAM, RAM, tamanho ROM e imagens renderizadas.
4. Validar mapas densos, Surf, saves antigos e desempenho antes de
   promover melhorias à ROM Master. Não refazer testes inalterados.

Fontes:
- https://gbadev.net/gbadoc/sprites.html
- https://gbadev.net/tonc/objbg.html
- https://github.com/rh-hideout/pokeemerald-expansion/blob/master/docs/tutorials/how_to_overworld_wild_encounters.md

## Resultados homologados em 30/10/2026

[Workflow ARM/GBA + mGBA #41048589031](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41048589031):
**SUCCESS e 18/18 verificacoes de gameplay** no emulador real mGBA.
Head de codigo validado: 4a4e73f789460512dd0e923573fce16b29a4b98d.
SHA256 ROM de teste: f581ba7e6229732faa17e79a11825682861c67dcbf6ee4670dabff20dd3279ae.
[Evidence artifact sem ROM/save](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41048589031/artifacts/12973108808).

### Runtime: Route29 com quatro OWEs e seguidor

- Pico OBJ allocation bitmap: 140/1024 tiles 4bpp = **4.480/32.768 bytes**.
- Minimo de tiles livres: 884, com menor sequencia contigua livre: 874 tiles = 27.968 bytes.
- Ate 18/64 sprites ativos (limite pool software, distinto dos 128 OAM hardware).
- Ate 11/16 slots de paleta OBJ ocupados.
- Duplicatas EXATAS das 16 cores entre paletas carregadas: **0 em todas as amostras**.
- Apos batalha e fuga: 136 tiles OBJ alocados, 8 paletas; o loop OWE e follower seguem vivos conforme os 18 testes.
- Estes numeros sao somente do Route29, nao FPS, DMA, tiles BG, sprites gigantes, Surf ou saves antigos.

### Inventario de formas declaradas na fonte World (geracoes 1-9)

- 1.364 inicializadores de especie examinados.
- 1.272 macros de overworld 32x32 e 42 macros 64x64, inclusive variacoes femininas.
- Esses valores sao **declaracoes source-only**, nao especies jogaveis ou sprites decodificados.

### Custos observados no ELF real

O script graphics_linker_audit.py categorizou **5.426.260 bytes** de
simbolos graficos efetivamente vinculados na ROM ARM, incluindo:

| Categoria | Bytes vinculados |
| --- | ---: |
| Overworld (gObjectEventPic_*) | 3.298.432 |
| Front sprites de batalha | 854.472 |
| Icones Pokemon | 720.896 |
| Back sprites de batalha | 468.628 |
| Paletas comuns de overworld | 20.448 |

As outras categorias constam no JSON. Esse valor **nao e cobertura total
do grafico**: prefixes conhecidos podem deixar outros dados de fora,
alguns simbolos sao aliases e parte do binario nao tem simbolos de asset.

### Proximas escolhas tecnicas

O gargalo demonstrado nesta rota NAO e OBJ VRAM. Paletas chegam a 11/16,
mas nao encontramos duplicata de cores carregadas ali. Logo, nao fundir
paletas automaticamente nem ligar OW_GFX_COMPRESS para folhas inteiras.

O maior alvo medido em bytes ROM sao os frames de overworld.
O proximo experimento deve avaliar **compressao por frame ou reutilizacao
exata de frames** em branch separada, com frame/paleta original preservado
e testes de ciclos, RAM temporaria, OBJ VRAM e capturas pixel-perfect.
**Nenhuma economia adicional dessa ideia foi demonstrada ainda.**

M8 permanece intacta. Nao fazer merge desta PR experimental.
