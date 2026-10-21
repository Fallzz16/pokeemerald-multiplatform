# Kanto V0.9 — cinco treinadores originais de Viridian Forest

Base: V0.8 commit `44a893d644a74644ed8b32ff0805ff9370e1b6fb`, workflow e compilação Windows aprovados. Fonte `pret/pokefirered` SHA `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`.

**Implementado no código:** os Bug Catchers Rick, Doug, Sammy, Anthony e Charlie são inseridos nas suas posições originais em Viridian Forest; usam os mesmos Pokémon, níveis e ordem de equipe da fonte FireRed, bem como os sprites e classe Bug Catcher disponíveis no Emerald. Scripts `trainerbattle_single` utilizam novos textos curtos provisórios, sem importar eventos de história ou interferir nas falas de Hoenn.

**Persistência da vitória:** Emerald Hybrid já reserva `MAX_TRAINERS_COUNT 864` e usa `TRAINERS_COUNT 855`. Os cinco adversários recebem os IDs 855–859, dentro dos **nove espaços de flags de treinador previamente reservados**. A contagem utilizada sobe a 860, mas o máximo e o layout do save permanecem inalterados. Restam 4 posições nesse intervalo; expandir além exige desenho de save/flags próprio, não reutilizar IDs antigos de Hoenn.

Os 84 mapas existentes e as flags de itens V0.8 permanecem na mesma ordem. Workflow `kanto-v09-viridian-trainers.yml` checa equipe, constantes, posição dos NPCs e compilação Windows.

**Importante:** CI e cross-build não provam IA, visão dos treinadores, captura, experiência, flag após salvar nem regressão de save; testar em execução Windows com cópia. Nenhum outro treinador dos 84 mapas foi importado. É a primeira batalha com NPC em Kanto, NÃO campanha completa. Não mesclar sem QA real e análise de compatibilidade multiplayer.
