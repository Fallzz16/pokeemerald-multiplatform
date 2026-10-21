# Kanto V0.16 — quatro líderes e insígnias independentes

Base: `feature/kanto-v15-indigo-league`, commit `36ce563941cb0d264c3ad8c376fd928c3d8b615b`. Fonte FRLG pinada: `pret/pokefirered` em `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`.

## Implementação
Os ginásios originais de Pewter, Cerulean, Vermilion e Celadon recebem Brock, Misty, Lt. Surge e Erika em suas **coordenadas originais**, com equipes, níveis, golpes e itens consumíveis de FireRed. As batalhas usam o motor Emerald e os **quatro IDs de treinador ainda disponíveis (860–863)**, após os cinco Bug Catchers já importados. `TRAINERS_COUNT` passa a 864, igual ao `MAX_TRAINERS_COUNT` de 864, **sem aumentar o campo de flags no save**.

Após vitória, cada líder aciona sua própria insígnia de Kanto (BOULDER, CASCADE, THUNDER, RAINBOW) e oferece sua TM original, com uma flag distinta que impede receber o item repetidamente. São oito flags novas alocadas em números anteriormente livres, após as **160 flags anteriores de pickups** (75 visíveis, 85 escondidos). Os oito badges de Hoenn continuam intactos. Retratos/sprites são equivalentes TEMPORÁRIOS do Emerald; ainda falta importar os originais FireRed.

O total de mapas permanece 114 em dois grupos, mantendo todos os IDs e flags anteriores. A workflow `kanto-v16-first-four-gym-leaders.yml` valida source parties, flags sem colisões, os quatro NPCs, batalha, recompensa e compilação Windows.

## Limitações críticas
- **Nenhum treinador adicional cabe no campo original de 864 flags de batalha.** Não acrescentar IDs >=864 sem projetar persistência nova, mantendo compatibilidade de saves anteriores.
- Não há puzzles funcionais completos, bloqueios de história, gráficos dos líderes originais, textos originais, progressão nacional integrada ao PokéNav nem feedback de insígnia na Trainer Card.
- Vencer quatro líderes não deve ser tratado como campanha de FireRed concluída.
- QA humano obrigatório: entrar em cada ginásio, acionar luta, perder/vencer, verificar insígnia e TM após salvar/reabrir, viagem de volta a Hoenn, e comportamento de derrota em Kanto. Os testes automatizados não substituem essas verificações.
- PR draft, sem merge até QA.

**Compatibilidade de constantes de TMs:** FireRed usa nomes semânticos (`ITEM_TM_ROCK_TOMB` etc.) e Emerald usa números. Correspondências originais verificadas: Brock `ITEM_TM39` (Rock Tomb), Misty `ITEM_TM03` (Water Pulse), Lt. Surge `ITEM_TM34` (Shock Wave), Erika `ITEM_TM19` (Giga Drain). São as mesmas TMs, não itens inventados.
