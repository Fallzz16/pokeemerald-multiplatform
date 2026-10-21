# Kanto V0.12 — 15 andares adicionais originais de FireRed

Base: Kanto V0.11 (commit 9d121938b0cab40c201e392e5f79d0b29ba04b15). Fonte pinada pret/pokefirered ce6406d8c2eaf46d543c8a2606de0c3cb1951982.

Geometria importada: Victory Road 1F–3F (3); Pokémon Mansion 1F–3F e B1F (4); Cerulean Cave 1F, 2F, B1F (3); Seafoam Islands 1F e B1F–B4F (5). Total: 15 novos mapas, 99 no grupo Kanto.

Preservação de saves: os primeiros 84 IDs permanecem na mesma ordem, bem como os 42 itens visíveis e 77 itens escondidos antigos (119 flags). O importador não adiciona os novos mapas à lista legada de alocação de itens. Para importar novos pickups no futuro, criar uma nova sequência de flags após os 119 anteriores.

Novos tilesets de Cave/Seafoam/Mansion/Cerulean, layouts e bordas originais, warps internos e saídas para Cerulean, Route20, Route23 e Cinnabar remapeadas. Sem NPCs, treinadores, puzzles de pedras/estátuas, fluxo de água especial, lendários ou missões originais neste lote. Algumas quedas são unidirecionais como na fonte, não presumir reciprocidade.

Workflow kanto-v12-major-dungeons.yml verifica 99 mapas, primeiros 84 IDs inalterados, bytes dos layouts, flags antigas e Windows build. Ainda NÃO comprova colisão/visibilidade, música, progressão ou save/load em gameplay. PR draft sem merge.