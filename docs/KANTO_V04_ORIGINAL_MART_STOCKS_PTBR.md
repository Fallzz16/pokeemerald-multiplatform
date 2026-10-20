# Kanto V0.4 — estoques verdadeiros dos mercados de FireRed

A partir de V0.3, esta fase preserva os **38 exteriores e 17 interiores** já incluídos na build e mantém os IDs existentes. Não cria mapas novos nem altera o formato do save.

O importador `tools/kanto/import_exteriors.py` extrai as listas `ITEM_*` **na ordem original** dos oito mercados de Viridian, Pewter, Cerulean, Lavender, Vermilion, Fuchsia, Cinnabar e Saffron a partir de `pret/pokefirered` no commit fixado `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`. Não inventa mercado em Celadon, cuja loja principal é um Department Store.

Cada lista original é validada quanto a constante existente no Emerald, ausência de duplicações e terminação com `ITEM_NONE`. O resultado usa `.short ITEM_*` mais `pokemartlistend`. Nenhum script de história FireRed é executado diretamente.

A workflow `kanto-v04-original-mart-stocks.yml` testa o parser com fixtures e compara os estoques de oito lojas aos dados originais antes da compilação Windows.

**Limites:** NPCs extra e histórias de cada loja, Ginásios, cavernas, Centro Pokémon 2F, respawn independente em Kanto e QA manual de compra/cura/save seguem pendentes. O CI não equivale a teste de gameplay. PR #28 preservada; não mesclar até QA.
