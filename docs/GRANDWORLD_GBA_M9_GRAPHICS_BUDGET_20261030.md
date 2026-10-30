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
