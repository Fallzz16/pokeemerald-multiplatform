# Kanto V0.18 — treinadores comuns de Route 3 e Mt. Moon

**Base:** Kanto V0.17, commit `7b23f5211f8adc315bc4b439ed6ee4e1a1b4eba7`, workflow Windows aprovado. **Fonte:** `pret/pokefirered` pinada no SHA `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`.

Foram portados mais **cinco Bug Catchers de FireRed**: Robby e Kent em Mt. Moon 1F; James, Greg e Colton na Route 3. Coordenadas, alcance de visão, sprites da classe, equipes, espécies e níveis vêm da fonte original. Scripts de batalhas usam o motor Emerald e textos curtos provisórios. Os cinco complementam os cinco Bug Catchers de Viridian Forest e oito líderes, totalizando **18 treinadores reais** de Kanto com batalhas no código.

## Persistência e compatibilidade
Os novos IDs **868–872** seguem os quatro IDs remapeados em V0.17; `GetTrainerSaveFlag()` em `src/battle_setup.c` traduz os novos cinco IDs para flags salvas previamente livres e **não modifica** a relação antiga para IDs 0–863 nem `MAX_TRAINERS_COUNT=864`/SaveBlock. `TRAINERS_COUNT=873` regula somente o total de dados de treinador. Foram acrescentadas cinco flags depois dos 180 valores já reservados em V0.17; não reordenar flags de versões anteriores.

Não há novos mapas: 114 mapas registrados em dois grupos, nenhum ID de mapa alterado. Nenhuma mudança nas 8 insígnias Hoenn, 8 badges de Kanto nem 160 itens originais.

## QA
A workflow `kanto-v18-moon-route3-trainers.yml` testa os cinco NPCs contra FireRed, IDs, flags únicas, scripts, dois grupos de mapas e cross-compila Windows. Só publicar como **preview de teste**. Falta homologação in-game de visão de treinador, perda/vitória, persistência e recarregamento de saves e LAN.

## O que ainda falta
Treinadores das outras rotas, cavernas e ginásios; puzzles, NPCs não treinadores, Team Rocket, Silph, Elite Four/Champion e Hall of Fame; assets originais dos líderes, Kanto no mapa/PokéNav/Fly, QA de todos os recursos no Windows e Android/LAN. Oito líderes disponíveis não equivalem a oito ginásios completos.
