# Kanto V0.13 — itens originais das quatro dungeons

Deriva da V0.12 compilada, commit `55b29648f1ec9a03d41adb9196fb4ee551fae672`. A V0.12 introduziu a geometria de 15 mapas adicionais (Victory Road, Pokémon Mansion, Cerulean Cave e Seafoam Islands).

Esta etapa acrescenta **33 Poké Bolas com itens visíveis** e **8 itens escondidos** exatamente nas posições originais de FireRed. As entradas visíveis usam `finditem ITEM_*` do Emerald, scripts originais só como fonte de constantes de itens (não são executados scripts de história); os escondidos mantêm quantidade e `underfoot`.

## Integridade de saves
Existem 189 flags `FLAG_UNUSED_...` disponíveis no pool definido. V0.11 já utiliza 42 para itens visíveis e 77 para escondidos. V0.13 aloca 41 **após** os 119 valores usados, sem recolocar itens nem renomear flags antigas: o total é 160 flags e o pool restante é 29. Não há alteração no formato SaveBlock ou IDs de 99 mapas.

Nunca adicionar os 15 mapas novos às listas de alocação originais V0.8/V0.11, pois isso deslocaria as flags dos itens antigos. A nova função `import_kanto_v12_pickups` possui reserva isolada e etiquetas `FLAG_KANTO_V12_ITEM_XXX` e `FLAG_KANTO_V12_HIDDEN_XXX`.

## Testes e pendências
Workflow `kanto-v13-dungeon-pickups.yml`: checar contagem 33/8, 119 flags anteriores intactas, alocação sem colisão, scripts e posições, 99 mapas e build Windows. Não é confirmação de que itens estão acessíveis ou que persistem após save/reload no jogo real. Pokémon Mansion, Seafoam e Victory Road ainda requerem puzzles, treinadores e eventos. Também faltam Lendários, ginásios, NPCs e QA manual Windows/multiplayer/Android.

**Não mesclar até validar** coleta de pelo menos dois itens antigos e novos, salvar/recarregar, Itemfinder, derrotas em Kanto, retorno a Hoenn e comparação com save histórico.
