# Grand World GBA — experimento da base-mestre otimizada

**Status:** candidato experimental, NÃO integrado. Branch isolada
`experiment/grandworld-gba-master-rom-space-20261029`; deriva do HEAD da PR #103
(`0649364aee330d4753af90dbdaeaf989687ddba0`). Preserva M8, PR #102,
tradução, personagens, mapas das três regiões, encontros, seguidores e saves.
**Somente GBA ARM**: nenhum binário Windows/SDL2/web substitui este jogo.

## Objetivo
Uma fonte reutilizável para ROMs derivadas (temas, Pokédex, histórias e regiões)
sem refazer a engine. O primeiro incremento mede ganho de espaço em **código
ARM/Thumb** com GCC `-Os` (`make modern O_LEVEL=s`) comparado ao build
`-O2` homologado. Não remove espécie, mapa, som, arte, evento ou código
necessário. Nenhuma otimização é aprovada por parecer menor, apenas por
**linker + compilação real + gameplay mGBA**.

## Evidência de referência imutável
- [M9, execução #40974046849](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40974046849):
  ARM/GBA + mGBA Route29, 18/18 PASS.
- ROM SHA-256 (identidade, não distribuída):
  `15017a9119b1c29d0f56835bb65a0c3f016d0059c3bb56be8363db05de7eac44`.
- Linker: ROM **24.564.352 B**; EWRAM **235.300 B**; IWRAM **28.200 B**.
- Capacidade ROM padrão **33.554.432 B**; cabeçalho GBA BPEE,
  reserva obrigatória de 1 MiB de ROM, 8 KiB EWRAM e 2 KiB IWRAM.
- Registrado em `qa/gba/baselines/m9_route29_18of18_budget.json`.
  O arquivo `.gba` é preenchido até 32 MiB; **poda do preenchimento ou ZIP
  do arquivo não cria espaço útil no cartucho**.

## Modificações presentes no experimento
1. Workflow `grandworld-gba-master-rom-space.yml` faz checkout da engine
   **World fixada** em `15d3888b0d81322a04d3c71b0bce18948761ee44`,
   aplica os mesmos adaptadores do M8/M9 e compila com `O_LEVEL=s`.
2. `master_rom_compare.py`: calcula diferenças reais de ROM/EWRAM/IWRAM
   contra a linha de base, rejeitando hashes iguais, ROM inválida,
   relatórios inconsistentes e violações de reservas. Não promete FPS, saves
   ou gameplay.
3. `master_asset_inventory.py`: inventaria hashes SHA-256 de recursos
   `graphics/` e `sound/`. Duplicatas binárias são **candidatas a auditoria**,
   não economia comprovada na ROM. Não apaga, recomprime nem reescreve nada.
4. O workflow exige **18/18 de gameplay real mGBA** inclusive OWE gerado,
   seguidor, movimento, interação, batalha, fuga, retorno e rodízio; só depois
   aprova uma redução de ROM **sem aumento estático EWRAM/IWRAM**.
5. Resultado e inventário gerados em JSON; artefatos de CI somente logs,
   capturas, símbolos e relatórios, sem ROM nem dados de save.

## Perfis para futuras variantes (planejamento, não resultados)
- `baseline`: GCC `-O2`, compatibilidade demonstrada pela execução referida.
- `space-candidate`: GCC `-Os`, candidatura à base-mestre; ainda requer CI
  verde e aferição de FPS.
- `release+LTO`: World possui opção RELEASE/LTO, mas o pipeline de compilação
  usa CC1 -> assembler; **não assumir eficácia ou compatibilidade do LTO
  sem experimento binário separado e testes de gameplay**.
- `asset-dedup`: revisão de referências e paletas de duplicatas encontradas.
  Descartar um gráfico só após demonstrar que todas as referências e
  variações (shiny, feminino, evento, seguidor) continuam idênticas.
- `library`: toda espécie/forma será indexada por ID, evolução, batalha,
  ícone, cry, paleta, overworld e habitat. Ativar 1.025 espécies requer
  orçamento, QA e **migração de saves**; `P_FAMILY_*` e limites de Pokédex
  podem alterar o SaveBlock, alertado pela própria engine.

## Restrições de hardware e riscos
- GBA padrão: ROM 32 MiB, EWRAM 256 KiB, IWRAM 32 KiB, VRAM 96 KiB,
  128 slots OAM, paletas limitadas. Preservar folga para novos Pokémon.
- **Não** ligar `OW_GFX_COMPRESS` indiscriminadamente: a configuração
  fixada mantém `FALSE` porque compressão de folhas inteiras pode
  esgotar OBJ VRAM com wild OWEs.
- `-Os` reduz o tamanho de alguns códigos, mas pode mudar o tempo de
  execução; **18/18 mGBA não mede FPS ou ciclos**. Homologar performance
  real em áreas densas e saves existentes antes de declarar perfil padrão.
- Não mesclar PR #103 automaticamente. O resultado experimental deve
  primeiro passar checks e revisão, depois ser promovido explicitamente.

## Referências
- https://gbadev.net/gbadoc/memory.html
- https://github.com/rh-hideout/pokeemerald-expansion/blob/master/Makefile
- https://github.com/rh-hideout/pokeemerald-expansion/issues/5169
- https://github.com/Fallzz16/pokeemerald-multiplatform/pull/103
