# Kanto V0.8 — item balls originais com persistência

Base: Kanto V0.7 commit `9f7edfe6d02140e08aedd94cc382412bb0b24998`, compilação Windows e auditoria de conectividade específicas aprovadas.

**Novo comportamento:** o importador lê exclusivamente os objetos `OBJ_EVENT_GFX_ITEM_BALL` dos exteriores e dungeons de FireRed já presentes, junto aos seus scripts `data/scripts/item_ball_scripts.inc`. Gera itens em posições originais, usando `finditem ITEM_*` do motor Emerald em vez de copiar rotinas de história incompatíveis.

**Saves:** cada Poké Bola ganha uma flag permanente isolada `FLAG_KANTO_ITEM_NNN`, aliada a uma constante `FLAG_UNUSED_0x...` previamente documentada como não utilizada em `include/constants/flags.h`. Não amplia os structs de save nem altera flags de Hoenn. O algoritmo de numeração é **append-only**, ordenado pelos 38 exteriores originais, nove mapas da V0.6 e quinze da V0.7, sempre nesta mesma ordem para preservar saves que tenham coletado itens. Ao importar novas áreas futuramente, acrescentá-las no final e nunca reordenar listas anteriores.

**Proteções:** script e item devem existir no projeto de origem, as flags devem estar disponíveis e os objetos não podem colidir em suas coordenadas com os eventos já gerados. Falhar e bloquear importação se itens não forem compatíveis ou pool de flags acabar. CI `kanto-v08-persistent-items.yml` executa testes com fixtures, confere objetos/flags/itens, testa grafo de 84 mapas e compila Windows.

**Não feito:** itens ocultos de chão, treinadores/NPCs, história Rocket, ginásios, centro de cura respawn em Kanto, efeitos especiais/colisão real, save e LAN/Android homologados. É uma nova camada de conteúdo e testes, mas não equivale a 50% de gameplay comprovado.
