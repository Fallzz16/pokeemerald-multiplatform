# Kanto V0.12 — quatro conjuntos de cavernas originais

## Foco
Base V0.11 aprovada em workflow específico, commit `9d121938b0cab40c201e392e5f79d0b29ba04b15`, branch `feature/kanto-v12-four-dungeons`.

## Conteúdo implementado
- **Victory Road:** 1F, 2F e 3F (3 mapas).
- **Pokémon Mansion:** 1F, 2F, 3F e B1F (4 mapas).
- **Cerulean Cave:** 1F, 2F e B1F (3 mapas).
- **Seafoam Islands:** 1F, B1F, B2F, B3F e B4F (5 mapas).

Todos usam layouts, dimensões, blocos, bordas, tilesets e paletas convertidos a partir da fonte `pret/pokefirered` pinada em `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`. Os warps internos do conjunto são validados com IDs reais da fonte; os externos para Route20, Route23, CeruleanCity e CinnabarIsland são remapeados e anexados sem alterar warps anteriores. Os encontros selvagens originais de FireRed são integrados onde aplicável.

Total **99 mapas registrados** em Kanto, os primeiros 84 permanecem na ordem exata anterior. Os 42 itens visíveis, itens escondidos, nove Centros Pokémon de whiteout, cinco treinadores de Viridian Forest e inventários das lojas anteriores continuam estáveis; **itens e NPCs específicos dos novos 15 mapas não foram importados ainda** para preservar a alocação de flags das versões anteriores.

## Limites de jogabilidade
Seafoam possui puzzles de Strength e correntes aquáticas que exigem portar eventos/comportamentos originais; Pokémon Mansion necessita interruptores/portas de estátuas, Victory Road exige puzzles com Strength e Cerulean Cave possui progressão dependente de história. A geometria não comprova que esses desafios sejam solucionáveis. Treinadores, itens e encontros de lendas/chefes não foram importados; acesso pode depender de requisitos ainda não implementados.

## Verificações
Workflow `kanto-v12-four-dungeons.yml`: igualdade byte-a-byte de mapa/layout, 15 IDs append-only, checagem recíproca de warps, encontros e build Windows, além do relatório de alcançabilidade de Kanto. QA manual com saves descartáveis deve inspecionar movimento, obstáculos, portas, batalhas, saves e retorno a Hoenn. PR draft sem merge. Rollback da versão original está preservado.
