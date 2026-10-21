# Kanto V0.7 — passagens subterrâneas, Rock Tunnel e Pokémon Tower

Base: V0.6, commit `dc5e692faccd57ea39a897c1a259cfb2b65db3a8`, workflow específico Windows aprovado.

**15 novos mapas:** 6 UndergroundPath (corredor norte/sul e leste/oeste, entradas Route5/6/7/8), RockTunnel_1F, RockTunnel_B1F, e PokemonTower_1F até PokemonTower_7F com escadas e saída para Lavender.

Importados layouts, blocos, bordas, tilesets próprios de FireRed e eventos de portas (não scripts de história) a partir de `pret/pokefirered` SHA `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`. Os índices de warp originais interiores são preservados; destinos para exteriores remapeiam os índices gerados depois dos serviços e portões. Tabelas selvagens **FireRed** nas áreas aplicáveis. Música provisória compatível; NPCs/eventos de história ainda não importados.

**Total: 84 mapas registrados em Kanto** (incluindo cais K0). IDs 0–68 mantidos exatamente como na V0.6. O importador não altera dados nem saves existentes de Hoenn. Checklist de QA: `.github/workflows/kanto-v07-underground-rock-tower.yml` verifica 15 mapas, blocos bytes iguais, destinos de warp recíprocos, IDs estáveis e cross-build Windows.

**Auditoria adicional:** `tools/kanto/reachability.py` calcula alcançabilidade *teórica* de mapas a partir de Vermilion por conexões e warps, gera `kanto-v07-reachability.json`. Não valida colisões nem NPCs nem garante jogabilidade. O resultado deve apontar regiões desconectadas e orientar o próximo lote.

**Pendências críticas:** Pokémon Tower requer eventos Ghost/Silph Scope e Rocket, Rock Tunnel requer comportamento de Flash, cenas de história e treinadores de ambas áreas, progressão por ginásios, heal/whiteout regional, salvar/reabrir em cada cidade, QA humano de gameplay e multiplayer, Android. Não anunciar Kanto completa, nem 50% de gameplay sem testes reais.
