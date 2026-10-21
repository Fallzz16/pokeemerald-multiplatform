# Kanto V0.14 — objetos coletáveis originais nas cavernas grandes

Base preservada: Kanto V0.13 commit `c0eafc930e7f14fdd12c4c8f2bb61ff1e024b07a`; fonte `pret/pokefirered` SHA `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`.

## Implementação
A V0.12 converteu Victory Road, Pokémon Mansion, Cerulean Cave e Seafoam Islands, mas ainda sem seus itens originais. A V0.14 acrescenta:
- **33 itens visíveis** (Poké Bolas), preservando origem, posição, Pokémon Ruby/Emerald `finditem` e identidade do item;
- **8 itens ocultos**, com localização, quantidade e `underfoot` da fonte FireRed;
- **41 novas flags de save isoladas**, alocadas somente em bits `FLAG_UNUSED_0x...` ainda não usados pelas **42 flags de itens visíveis e 77 ocultos** anteriores. Nenhum ID de mapa muda; continuam 107 mapas de Kanto.

O importador lê os arquivos originais de mapas e `data/scripts/item_ball_scripts.inc` para gerar os objetos e scripts compatíveis com Emerald, recusando itens sem constantes, posições duplicadas ou flags repetidas. Regra permanente: não renumerar `FLAG_KANTO_ITEM_*`, `FLAG_KANTO_HIDDEN_*`, `FLAG_KANTO_V14_ITEM_*` ou `FLAG_KANTO_V14_HIDDEN_*` depois da distribuição.

## Validação
`kanto-v14-major-dungeon-pickups.yml` confirma **33+8 itens**, correspondência dos objetos com FireRed, flags salvas sem sobreposição, 107 IDs, scripts e mapas de ginásio preservados, build Windows. Falha impede merge.

## Ainda falta
Treinadores, líderes, insígnias, puzzles e narrativa originais; sistemas de terreno com interação especial; QA in-game das coletas (incluindo save/reload e Itemfinder); 2F Centros, Pokémon Center PC, Fly/PokéNav Kanto; multiplayer e Android. Sem homologação humana, o ZIP segue preview experimental, não versão completa.
