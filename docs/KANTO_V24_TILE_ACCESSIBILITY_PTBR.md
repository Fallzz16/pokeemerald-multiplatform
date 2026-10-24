# Kanto V0.24 — Auditoria estática de acessibilidade por metatiles

## Estado verificado em 23/10/2026
- Branch `feature/kanto-v24-tile-accessibility-qa`, derivada da V0.23 em `62a9e03174245a2ef9ec36a73c481d09543ddf09`.
- Commit de código/CI verificado: `f36abb8ba3fa7234b6a9a65fa7c9ce142ca6d5ea`.
- GitHub Actions [39918532192](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/39918532192): workflow de Kanto e build Windows **SUCCESS**. Artefato `KANTO_V24_MT_MOON_ROUTE3_TRAINERS_UNTESTED_WINDOWS`, ID `12485394284` contém executável, SDL2, sha256, checklist e relatório JSON de colisão.
- Ferramenta `tools/kanto/tile_audit.py`; testes de unidade `tests/test_kanto_tile_audit.py`. O relatório é gerado após materializar FireRed na revisão fixa `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`.

## Números observados no relatório JSON produzido pelo CI

| Medida | Valor |
|---|---:|
| Mapas auditados | 114 (2 grupos) |
| Tiles nominalmente livres | 53.756 |
| Tiles nominalmente bloqueados | 58.546 |
| Mapas com avisos | 25 |
| Mapas com eventos fora dos limites | 0 |
| Mapas com eventos potencialmente inacessíveis | 4 |
| Mapas com pares de warps em componentes desconectados | 21 |
| Gameplay, elevação ou saves validados | **Não** |

### Quatro eventos a conferir prioritariamente no emulador
1. `Kanto_Harbor`: NPC índice 1, coordenadas (8,7), sem tile nominalmente livre adjacente.
2. `Kanto_PokemonLeague_LoreleisRoom`: warp 0 em (6,12).
3. `Kanto_PokemonLeague_BrunosRoom`: warp 0 em (6,12).
4. `Kanto_PokemonLeague_AgathasRoom`: warp 0 em (6,12).

Os quatro avisos **não provam erros**: scripts, mapas de colisão, tiles especiais, posições de NPC e transições podem explicar os casos. Inspecionar o jogo antes de modificar qualquer mapa.

### Vinte e um mapas com warps separados pelo grafo estático
`Kanto_CeruleanCity`, `Kanto_Route2`, `Kanto_Route4`, `Kanto_Route10`, `Kanto_Route20`, `Kanto_Route23`, `Kanto_MtMoon_B1F`, `Kanto_MtMoon_B2F`, `Kanto_RockTunnel_1F`, `Kanto_RockTunnel_B1F`, `Kanto_VictoryRoad_2F`, `Kanto_PokemonMansion_1F`, `Kanto_PokemonMansion_2F`, `Kanto_PokemonMansion_3F`, `Kanto_CeruleanCave_1F`, `Kanto_CeruleanCave_2F`, `Kanto_SeafoamIslands_1F`, `Kanto_SeafoamIslands_B1F`, `Kanto_SeafoamIslands_B2F`, `Kanto_SeafoamIslands_B3F` e `Kanto_SaffronCity_Gym`. Alguns são puzzles, águas, pisos especiais ou corredores com entradas independentes; **não** corrigir colisão somente pelo aviso.

## Escopo real da ferramenta
A auditoria lê `map.bin`, dimensões, máscara de colisão (0x0C00), componentes 4-direções e eventos de mapa. Não modela Surf, correntes, bordas, Strength, Cut, scripts, triggers, altura, sprites dinâmicos, save/reload ou movimento real. O grafo de acessibilidade anterior (`kanto-v07-reachability.json`) também é estático.

## QA manual indispensável
- Usar cópias de saves e instalação isolada do Windows, **nunca** sobrescrever saves do jogador.
- Caminhar Harbor, ginásios, League, Mt. Moon, rotas e as 21 situações listadas; verificar interação na frente dos NPCs e warps em ambos os sentidos.
- Testar escolha de fóssil com mochila cheia, segundo fóssil, salvar/reabrir, derrota e retorno a Hoenn.
- Rodar com dois computadores para Cable Club e LAN somente após passos anteriores; não interpretar compilação como prova de rede.

## Reproduzir
```bash
python -m unittest discover -s tests -p test_kanto_tile_audit.py -v
python tools/kanto/import_exteriors.py --firered firered-source --emerald . --report kanto-exteriors-import.json
python tools/kanto/tile_audit.py --emerald . --output kanto-v24-tile-audit.json
```

## Garantias e rollback
As ferramentas não editam saves, flags, Trainer IDs ou layouts; a nova auditoria opera de modo **somente leitura** sobre mapas já importados. Rollback: usar a branch anterior V0.23. PR V0.24 permanece rascunho até QA manual; o trabalho GBA moderno segue isolado na PR #61.
