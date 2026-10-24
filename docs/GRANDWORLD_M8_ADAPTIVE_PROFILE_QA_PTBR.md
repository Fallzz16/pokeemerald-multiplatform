# Pokémon Grand World — M8 perfil experimental Quetzal / decisões 1A 2C 3B 4B 5C

**Data:** 2026-10-24. **Base imutável:** PR #73 em `85bb2e478e06cd57e5623499389a905a190eb12c`, que por sua vez deriva do PR #70. **Objetivo:** FPS estável em mapas lotados (1A), sombras adaptativas (2C), avaliar cache e pré-carregamento seletivo (3B), mGBA/emuladores modernos em primeiro plano (4B), testar perfis agressivos isoladamente com rollback (5C).

## Implementado nesta branch experimental

1. `tools/grandworld/apply_quetzal_profile.py`: aplica perfil **somente depois** de `optimize_overworld_budget.py` do PR #70 em checkout **World isolado/pinado**. Faz preflight fail-closed de 4 arquivos antes de qualquer escrita, sem reconfigurar saves.
2. `include/config/wild_encounter.h`: `WE_VANILLA_RANDOM = TRUE` preservado; `WE_OW_ENCOUNTERS = FALSE` bloqueia geração aleatória de Pokémon selvagens visíveis no cenário. Encontros padrão permanecem, incluindo regras originais de cavernas, Surf e pesca — consultar regra específica do usuário caso ele tenha exigido proibir também esses meios. **Não afirmar cumprimento literal de apenas tiles de grama** sem ampliar a cobertura dos testes e decisões.
3. `src/wild_encounter_ow.c`: bypass após executar limpeza inicial de spawns gerados. Evita nova consulta ao cabeçalho de encontros em quadros subsequentes enquanto OWE está desativado; ganho de FPS ainda não medido.
4. `include/config/overworld.h`: volta `OW_OBJECT_VANILLA_SHADOWS = FALSE` no perfil opcional, mantendo a criação de sombras comuns, ao contrário da troca para jump-only do PR #70.
5. `src/field_effect_helpers.c`: conta sprites ocupados **durante a varredura existente de sombras duplicadas**, sem segundo loop. Para criação de *novas* sombras comuns exige 12 slots de reserva; jogador e acompanhante exigem 4. Sombras já criadas são mantidas (não eliminadas reativamente). É uma hipótese de qualidade visual vs ocupação, não um resultado de performance.
6. `tests/test_apply_quetzal_profile.py`: testes de idempotência, falha sem escrita parcial, configurações, proteção de salvamentos e contagem de reservas.
7. `.github/workflows/grandworld-m8-grass-adaptive.yml`: build modern de 32 MiB, `make validate`, medições de linker, auditoria LZ77, mGBA headless fixado com SmokeBoot/WorldTitle vinculados por MD5 da ROM; somente artefatos de diagnóstico, jamais ROM/save.

## Não implementado neste incremento

- **3B cache e pré-carregamento seletivo de novos recursos:** ainda não modificado; o motor World já usa rotinas LZ77 otimizadas e `OW_GFX_COMPRESS=FALSE` por restrições de VRAM. Primeiro medir cache misses/reloads, estabilidade de VRAM e diferenças de quadro, só depois implementar buffer de recursos com testes.
- Benchmark de FPS ou ciclos de CPU. SmokeBoot e WorldTitle demonstram boot/título, **não certificam exploração, sombras, encontros, batalhas ou saves**.
- Qualquer mudança em SaveBlock, regiões, histórias, equipe compartilhada, scripts, IDs, dificuldade, Pokémon selvagens, dados de batalha e multiplayer M9.
- Mesclagem com PR #73, PR #70 ou `main`; a branch continua isolada.

## Regra existente: encontros somente na grama

A configuração de encontros **visíveis no overworld** é desligada. Os encontros aleatórios clássicos do Emerald continuam ligados; estes também podem incluir Surf, pesca e cavernas. Se o requisito do usuário significar literalmente *nenhum* encontro fora de tiles de grama, isso exige mais uma alteração de gameplay e suíte específica. Não camuflar essa divergência: esta implementação **ainda não prova encontros exclusivamente na grama em sentido literal**.

## QA e aceite

- Fonte: pré-validação de âncoras e testes de configuração. `python3 -m unittest discover -s tools/grandworld/tests -p 'test_apply_quetzal_profile.py' -v`.
- Build: `make -C world modern -j2`, `make -C world validate`, tamanho/código/checksum e RAM EWRAM/IWRAM sob limite.
- mGBA: SmokeBoot e WorldTitle com status PASS específico do MD5 da ROM compilada, nenhum FAIL conflitante.
- **Pendente para adoção:** cenários com NPCs lotados, sombreamento, jogador/seguidor, água, combate, viagem Hoenn/Kanto/Johto, histórico de saves reais e comparação cronometrada de 1% low/frames lentos nos mesmos cenários e emulador.
- Aceite de produto: decisão do usuário **1A** é priorizar estabilidade real, não apenas diminuir ROM. Qualquer regressão de frames, tiles, sprites, crashes ou saves cancela promoção deste perfil.

## Rollback e escopo dos experimentos

Branch `perf/grandworld-m8-adaptive-grass-benchmark-20261024`, criada no PR #73 `85bb2e478e06cd57e5623499389a905a190eb12c`. Descartar somente este perfil experimental e o workflow; restabelecer PR #73 integralmente. Não modificar ROM distribuída, `main`, os PRs #68–#70, backups nem multiplayer.
