# M9 — encontros visíveis terrestres: orçamento de paletas OBJ

**Branch experimental**, derivada de test/grandworld-gba-m9-master-visible-configuration-20261027 (`c79209534ec519539a873a306a0fcf17c165daca`). **Não é uma alteração da M8 estável ou da PR #102.**

## Auditoria: o que a PKMN-World já oferece

Fonte fixada: evilchinesefood/PKMN-World@15d3888b0d81322a04d3c71b0bce18948761ee44.

- O motor existente é `src/wild_encounter_ow.c`: `UpdateOverworldWildEncounter()` seleciona tiles usando `MetatileBehavior_IsLandWildEncounter` na terra, consulta tabelas nativas e prepara um `ObjectEvent` com espécie, nível e movimento. Há interações por A/colisão e batalhas via `StartWildBattleWithOWE`.
- `include/wild_encounter_ow.h` limita OWEs gerados a **4**. O motor tem espera mínima de 30 frames e aumenta o intervalo conforme os OWEs ativos. Esta PR **não** eleva a densidade.
- A configuração World já habilita `WE_OW_ENCOUNTERS` e `WE_VANILLA_RANDOM` em paralelo, `OW_FOLLOWERS_ENABLED` e movimento restrito a metatiles e mapas. Pesca, Surf, cavernas e Rock Smash permanecem com seus caminhos originais.
- A M9 atual compõe a World original com adaptadores da M8. O workflow anterior compilava a ROM real, **mas não demonstrava gameplay de OWE gerado no mGBA**.
- `OW_GFX_COMPRESS FALSE` já é o perfil adotado para evitar esgotar a VRAM de sprites grandes; o perfil de sombras enxutas da M8 já procura preservar slots OAM.

## Defeito específico identificado

`CheckCanLoadOWE_Palette` exigia pelo menos um slot livre, mesmo quando as duas paletas necessárias (Pokémon e animação de aparição) **já estavam residentes**. Isso pode recusar OWEs gerados em mapas com muitas paletas de NPCs/seguidores. Com um único slot livre, também há falsa recusa quando uma espécie só usa paleta de sprite frontal, porque o identificador pesquisado não correspondia ao usado por `LoadDynamicFollowerPalette`.

**Correção integrada ao build experimental, não ao código-fonte do fork/PR #102:**

1. `tools/grandworld/patch_m9_owe_palette_budget.py` verifica flags de OWE, encontros aleatórios, seguidores e VRAM; valida os anchors exatos da World fixada; falha sem escrever se houver drift; e exige `--apply` explícito.
2. A função `GetDynamicFollowerPaletteTag` agora prevê o **mesmo fallback para tag `species`** usado pelo loader quando não há paleta OW específica. Mantém a escolha de paleta feminina normal/shiny condicionada à presença do recurso.
3. `CheckCanLoadOWE_Palette` contabiliza **quantas tags distintas ainda não estão carregadas** e compara com `CountFreePaletteSlots`. Assim, 0 slots livres é aceitável **somente se ambas as paletas já estiverem residentes**; se faltar recurso, o spawn é recusado sem desalocar paletas de terceiros.
4. Regressões de script cobrem idempotência proibida, anchors alterados, flags inválidas, modo somente leitura e escopo exato. **São testes de transformação de código, não execução de gameplay.**

### Lógica de orçamento

| Paletas faltantes | Slots livres | Resultado esperado |
| --- | ---: | --- |
| Nenhuma | 0 | Pode prosseguir à checagem de tiles |
| Uma | 1 | Pode prosseguir |
| Duas | 1 | Recusa segura |
| Uma | 0 | Recusa segura |
| Duas | 2 | Pode prosseguir |

Uma aprovação na checagem de paletas **não garante** sucesso de spawn: tile VRAM, object events, colisão e outros guards ainda precisam passar. Nenhuma alocação é forçada.

## Validação e critérios de aceite

O workflow M9 agora roda os testes Python da correção, faz preflight do motor fixado, aplica o patch após os adaptadores M8 + PT-BR, executa `git diff --check`, compila `make -C world modern`, verifica ROM de 32 MiB e cabeçalho GBA e publica **apenas relatórios/logs** (nunca ROM ou saves). O resultado de cada execução depende do Actions; não declarar PASS sem consultar o run.

**Aprovação de gameplay PENDENTE:** iniciar ROM real em mGBA, caminhar em mapa com grama (ex.: Route 29 ou Route 101), conferir um **OWE gerado**, sprite correto, movimento, contato/A e batalha/captura legítima; inspecionar retorno, seguidor, encontros aleatórios, limpeza em transição de mapa e pressão de paleta/OBJ. Capturas e traces precisam registrar hash da ROM e identificação do teste. Não usar apenas Pokémon de evento colocado manualmente, pois isso não prova geração automática.

## Riscos e limites

- Sem execução dinâmica, ainda não há medição antes/depois de taxa de geração, FPS, OAM, VRAM ou EWRAM. Esta otimização elimina uma falsa recusa **em princípio**, mas ganho medido será informado somente após teste controlado.
- O limite de quatro OWEs e as tabelas de habitats não foram alterados. Nenhuma espécie, asset Quetzal, save, formato de dados ou encontro tradicional foi modificado.
- O carregamento real ainda pode falhar por outros recursos; a mitigação é recusar sem crash, nunca desalocar seguidor/NPC para abrir espaço.
- Não fazer merge automático. A PR deve permanecer **draft** até um teste mGBA terrestre gerado, completo e reprodutível.

## Referências

- https://github.com/evilchinesefood/PKMN-World/tree/15d3888b0d81322a04d3c71b0bce18948761ee44
- https://rh-hideout.github.io/pokeemerald-expansion/tutorials/how_to_overworld_wild_encounters.html
- https://gbadev.net/gbadoc/memory.html
- https://gbadev.net/gbadoc/sprites.html
