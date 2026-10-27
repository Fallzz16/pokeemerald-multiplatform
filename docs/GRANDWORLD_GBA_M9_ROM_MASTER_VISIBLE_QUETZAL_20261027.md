# Pokémon Grand World GBA — M9 ROM Master (direção confirmada em 27/10/2026)

> ESCOPO: ROM real de Game Boy Advance `.gba`, baseada em `evilchinesefood/PKMN-World@15d3888b0d81322a04d3c71b0bce18948761ee44`, com Hoenn, Johto e Kanto. **Não** se refere ao jogo web. Esta proposta **não altera gameplay, saves, mapas, arte, espécies ou a M8 estável**.

## 1. Objetivo do jogador — a regra principal

Uma ROM Master que reúna as melhores funcionalidades de Pokémon, com **Pokémon selvagens visíveis e se movendo no overworld**, seguidores, regiões completas e progressão compartilhada, enorme coleção de espécies (objetivo até Gen 9), PT-BR, protagonistas com sprites próprios, eventos e pós-jogo. Preservar o caráter de GBA real e respeitar a memória/ROM do hardware.

**Não interpretar "Pokémon terrestre" como a categoria técnica `land_mons`:** a mesma categoria abrange certos pisos de cavernas. **Nunca deslocar peixes para grama para satisfazer a auditoria.** Água e pesca devem continuar funcionando.

## 2. Descoberta de fonte primária — já existe um motor de Pokémon visíveis

- No PKMN-World fixado, `include/config/wild_encounter.h` tem `WE_OW_ENCOUNTERS TRUE` e `WE_VANILLA_RANDOM TRUE`. O primeiro produz Pokémon visíveis gerados automaticamente; o segundo habilita encontros clássicos de passos. São sistemas distintos e podem coexistir.
- `include/config/overworld.h`: `OW_POKEMON_OBJECT_EVENTS TRUE`, `OW_FOLLOWERS_ENABLED TRUE`, `OW_GFX_COMPRESS FALSE`, `OW_SUBSTITUTE_PLACEHOLDER TRUE`, `OW_LARGE_OW_SUPPORT TRUE`; isso oferece base para seguidores, Pokémon como objetos, sprites grandes e fallback.
- `StandardWildEncounter()` original chama `MetatileBehavior_IsLandWildEncounter` para grama **e cavernas**, e `MetatileBehavior_IsWaterWildEncounter` para Surf. `RockSmashWildEncounter()` e `FishingWildEncounter()` têm seus próprios procedimentos.
- O adaptador M8 `tools/grandworld/optimize_overworld_budget.py` preserva explicitamente encontros visíveis. O script pós-M8 `tools/grandworld/apply_grass_only.py` é que muda `WE_OW_ENCOUNTERS` para FALSE, proíbe encontros fora de grama e bloqueia pesca/Rock Smash. **Esta política está em desacordo com a direção corrigida pelo usuário: NÃO aplicar `apply_grass_only.py` à ROM Master.**
- A documentação de expansão esclarece OWE gerados e manuais, comportamentos de perseguição/fuga, restrição por tile e uso das tabelas `WILD_AREA_LAND/WATER`. OWE podem ser limitados à grama/água por metatile, não precisam aparecer em estradas ou locais absurdos.

Fonte: https://rh-hideout.github.io/pokeemerald-expansion/tutorials/how_to_overworld_wild_encounters.html
Código fixado: https://github.com/evilchinesefood/PKMN-World/tree/15d3888b0d81322a04d3c71b0bce18948761ee44

**Consequência imediata:** abandonar o projeto de realocar 16 Pokémon predominantemente aquáticos para grama como "solução". Preservar PRs #84–#99 apenas como auditoria/QA histórico até reclassificá-las. Qwilfish em grama (PR #89, 8/8 experimental) é prova técnica, não uma distribuição aprovada. Bagon na caverna da PR #99 falhou sob o conjunto errado de regras; reavaliar depois no perfil Master sem falsificar o resultado anterior.

## 3. O que a biblioteca privada Quetzal realmente comprovou

Foram **abertos e lidos** `Quetzal_V7_00_CATALOGO_INDICES.zip` (dados/RELATORIO_V7.json, dados/VALIDACAO_V7.json, dados/pokemon_batalha.json, dados/overworld_ffp2.json) e `GrandWorld_MegaPack_Relatorio_V1.md`, disponíveis na Biblioteca do usuário. NÃO publicar ROM, imagens extraídas ou pacotes comerciais no repositório.

- ROM de origem da extração V7 SHA256 `920b43b15f86716fd42cb1f362ee158019cefcda811d47c213d2366cdf019265`. A versão da extração não deve ser confundida automaticamente com o Quetzal v0.9.1 atual.
- Catálogo V7: **1.530 registros de batalha**, **6.120 PNGs de front/back normais/shiny**, **3.060 PNGs de ícones** e **3.036 registros de gráficos overworld FFP2**; 1.206 no segmento normal, 1.206 em variantes de paleta e 624 gráficos extras de identidade incerta.
- `VALIDACAO_V7.json` registra `PASSOU` em integridade de **37.227 assets** da distribuição V7 (17.399 PNG, 19.828 GIF). Isto **não** prova identificação de cada espécie nem compatibilidade com a engine.
- **898** espécies-base possuem correspondência de overworld **inferida por sequência, não individualmente certificada**. Nos 1.530 registros de batalha, outros **632** estão `UNRESOLVED` quanto ao `overworld_normal_gfx`. Há **1.240 registros FFP2** sem nome individual comprovado. Os 113 personagens têm gráficos/animações, mas a correspondência exata nome↔slot não foi individualmente confirmada (relatório indica 0 confirmações).
- Exemplos existentes em batalha no catálogo: Sprigatito ID interno Quetzal 1214, Fuecoco 1217, Quaxly 1220, Lechonk 1244, Pawmi 1250, Charcadet 1264 e Tinkatink 1286. Todos esses exemplos têm **overworld_normal_gfx = null** no catálogo V7. **Esses IDs são da ROM Quetzal, não podem ser usados como IDs nacionais ou da World.**
- O MegaPack V1 contém **92.986 arquivos de assets únicos**, deduplicados por SHA-256 de **311.251 entradas** de várias coleções, com **67.890** classificados como overworld/animações. São *arquivos*, não 92.986 espécies/sprites únicos por Pokémon. Pokémon Reloaded permanece apenas catalogado, não foi incorporado como imagens nesse MegaPack.
- Para integrar Gen 9: criar crosswalk `species World → species Quetzal → forma → battle front/back → ícone → overworld normal/shiny → quadro/direções → paleta → origem/hash → verificação visual → validação no mGBA`. **Não** estimar `gfx` por deslocamento numérico em formas, nem atribuir automaticamente as 632 entradas sem OW resolvido.

Fonte complementar do motor: https://rh-hideout.github.io/pokeemerald-expansion/FEATURES.html (suporte de sprites até Gen IX e Pokémon seguidores, com habilitações dependentes de configuração).

## 4. Estado real e limites atuais do Grand World

- M8/PT-BR/6 protagonistas: menus de escolha reais **96/96** (https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40296022578); sprites dos seis protagonistas ainda são principalmente **recolorizações de Brendan/May**, não seis conjuntos individuais validados.
- `tools/grandworld/expand_gen4_pilot.py`: piloto experimental de **31 famílias Gen 4** e **12 famílias Gen 5 extras** com `--with-gen5-trial`. **Não declarar que a ROM atual já compila todas as gerações até 9.** World base desabilita famílias Gen4–9, com exceções de evoluções de linhagens antigas.
- Os relatórios da M8 registram builds O2 lean/full por volta de **24,6 MB** e cabeçalho de 32 MiB, mas números desta build anterior não equivalem à capacidade livre garantida depois de adicionar novas artes e espécies.
- O hardware GBA padrão mapeia até **32 MiB de ROM**, 256 KiB EWRAM, 32 KiB IWRAM, 96 KiB VRAM e 128 slots OAM. Cada espécie/forma/som/sistema disputa esses recursos; **não carregar a biblioteca ZIP inteira no cartucho**.
- A própria `include/config/species_enabled.h` da World alerta: alterar o limite de geração pode modificar os flags da Pokédex no save. Antes de habilitar grandes grupos, **congelar layout/IDs, comparar arquivos de save, definir migração ou incompatibilidade claramente**. Nunca prometer retrocompatibilidade sem ensaio.
- Provas anteriores: 51 suites World; 702 Save/Continue/multi-região; 96 heróis; 12/12 passo em grama; 33/33 captura/fuga. **Não duplicar essas suites sem uma mudança que as afete.** O sistema visível no novo perfil ainda exige evidência própria de gameplay.

Fonte sobre limites GBA: https://gbadev.net/gbadoc/memory.html

## 5. Backlog em ordem de implementação (GBA real, não Windows/SDL/web)

### P0 — restaurar e provar mundo vivo

1. Criar um perfil opt-in **M9 Master Visible** sobre a base M8/PT-BR, com `WE_OW_ENCOUNTERS TRUE`, `WE_VANILLA_RANDOM TRUE`, `OW_FOLLOWERS_ENABLED TRUE`, otimizações OAM da M8; pular `apply_grass_only.py`.
2. Auditar tipo real dos tiles e tabelas sem alterações automáticas. Pokémons terrestres na grama e terrenos adequados, caverna no subterrâneo, água em Surf, pesca via vara, Rock Smash nas rochas. A engine escolhe espécies da tabela do **habitat**, não pelo nome "land".
3. Escrever QA nova mGBA que exija sprite de Pokémon selvagem realmente renderizado/movimentando-se na tela, encontro por colisão/A, combate/captura autênticos e retorno; provar também encontros normais de caverna/Surf/pesca/Rock Smash por caminhos existentes. Não substituir por leitura estática de `#define`.
4. Testar OAM/VRAM em mapas densos com seguidor + NPCs + OWEs, mudanças de mapa e 60 FPS reais antes de definir spawn density. Garantir que o motor pule spawns por pressão em vez de crash. Não repetir a medição OAM antiga que contou sprites dummy fora da viewport.
5. Preservar encontros raros, shiny, repelente, roaming, criadores de eventos e encontros scriptados originais.

### P1 — pipeline gráfico Quetzal → World

1. Desacoplar arte do projeto web (somente inspiração e biblioteca verificada; jamais copiar alterações web de volta ao GBA).
2. Fazer piloto visual **apenas com uma espécie comum e comprovadamente identificada**, preferencialmente Bulbasaur/Pikachu (identidade e quadros validados por preview), converter palette 4bpp/tile 8x8/direções/anim e integrar no esquema nativo `OVERWORLD(...)`. Verificar tamanho, compressão, OAM, contraste e 240x160 mGBA.
3. Abrir amostras Gen9 **Sprigatito/Fuecoco/Quaxly** só após mapear graficamente `gfx` correto: atualmente OVERWORLD não identificado para essas espécies no catálogo V7. Ninguém deve alegar que já temos 3 OW prontos apenas por existir front/back de batalha.
4. Expandir para variantes shiny, formas, Megas, lendários, seguidores e montarias **aos poucos**. Não inserir arquivos massivos sem necessidade; medir ROM por família antes/depois.

### P2 — 3 regiões completas e estética da ROM Master

1. Revisar os 24 ginásios, três ligas, quests centrais, segredos, ginásios pós-jogo, Battle Frontier, regiões, viagem e itens/equipe/PC compartilhados sem novos bloqueios de save.
2. Substituir recolorações por sprites individuais e direcionais para **Brendan, May, Red, Leaf, Ethan e Lyra**; conferir intro, overworld, Surf, bicicleta, batalha, sprites com seguidor e identidade salva.
3. Integrar recursos modernos quando presentes/compatíveis: Mega Evolution, Z-Moves e outras mecânicas só após checar limites/código de World, UI, itens e estabilidade. A presença de uma *config* não é uma funcionalidade de campanha verificada.
4. Ajustar comportamento visível por espécie: passivos vagam, tímidos fogem, agressivos perseguem; água nunca cruza para a terra, grandes não cobrem portas/NPC. Usar movimentos OWE já disponíveis antes de inventar IA nova.

### P3 — Pokédex realmente enorme até Gen 9

1. Gerar inventário `species_enabled`, sprite de batalha, icon, follower/OW, cry, evoluções, ataques/abilidades, aquisição em região, habitat, evento e custos ROM.
2. Expandir **por família com dependências completas** e QA, iniciando por famílias ausentes cuja arte e engine estejam confirmadas. Não adicionar 339 famílias em lote sem orçamento.
3. Garantir captura/registro/evolução/troca/armazenamento/continuidade do save. Corrigir o caminho de aquisição, não forçar todos os Pokémon a aparecer na grama.
4. Eventos especiais, lendários e formas raras em mapas/quests adequados; capturar toda a Pokédex exige balanceamento e testes.
5. Multiplayer fica **adiado** até a single-player estar sólida. Mesmo que Quetzal demonstre coop, não copiar ROM/código fechado, nem prometer equivalência.

## 6. Critérios de aceite da primeira PR de código M9 Master

- Branch isolada e draft; manter PR #72 (M8), #80 (PT-BR), seus pais e todos os saves estáveis intactos.
- Build `make modern` real ARM GBA + hash, cabeçalho, orçamento ROM/EWRAM/IWRAM.
- Verificação estática das toggles corretas, seguida de screenshot/trace mGBA de OWE visível e batalha acionada naturalmente.
- Confirmar grama, caverna, Surf, pesca, Rock Smash em rotas plausíveis; ausência de travamentos.
- Conferir mapa com NPCs + seguidor + wild e OAM real, sprites corretos (sem Substitute indevido).
- Encontros aquáticos nunca movidos para grama por auditoria; antigas 16 propostas sob revisão.
- Sem upload de ROM ou save de terceiros; evidência apenas em hashes, screenshots e logs.
- Gate de saves se espécies/flags forem alteradas. Nenhuma merge automática sem demonstração.

## 7. Sobre esta branch

Somente documentação e planejamento fundamentado. **Nenhuma ROM atual foi corrigida, nenhuma família Gen9 foi ativada, nenhum Pokémon visível novo foi declarado testado.** Próxima PR de código precisa implementar os gates e provar no mGBA.

Último direcionamento recebido: **o jogador quer os Pokémon selvagens visíveis no mapa**, não escondidos em encontros exclusivos de grama.
