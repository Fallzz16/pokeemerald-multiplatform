# Kanto V0.11 — itens escondidos originais

## Fonte e estabilidade
Deriva da V0.10, usa `pret/pokefirered` no commit `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`. O importador adiciona eventos `bg_events` tipo `hidden_item` apenas nos mapas anteriores já importados (38 exteriores, nove da V0.6 e quinze da V0.7). Preserva item, quantidade, elevação, posição e parâmetro `underfoot` das versões originais de FireRed.

## Saves e compatibilidade
Cada item escondido tem uma flag persistente `FLAG_KANTO_HIDDEN_NNN` alocada em bits anteriormente reservados e livres do Emerald **depois** dos 42 itens visíveis V0.8. Proibido reutilizar flags, reordenar mapas anteriores ou trocar a revisão de FireRed. A V0.11 não amplia saves, não altera IDs dos 84 mapas, nem sobrescreve Hoenn, e mantém independentes as variáveis de respawn regionais da V0.10.

## Qualidade
`kanto-v11-hidden-items.yml` testa invariância das 42 flags antigas, inexistência de colisões entre flags de itens visíveis/ocultos, origem exata das coordenadas/dados, quantidade, e cross-compila Windows. Os testes com fixtures verificam um item verdadeiro e a recusa de itens ausentes.

**Ainda pendente:** QA in-game do Itemfinder, coleta, flags após salvar/reabrir, sistema de whiteout da V0.10, gráficos especiais, ginásios e NPCs originais, LAN/Android. Não equiparar número de itens a porcentagem jogável. Não mesclar sem QA humano com saves descartáveis.
