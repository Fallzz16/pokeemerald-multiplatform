# Pokemon Grand World GBA PT-BR — etapa 10

**31/10/2026 — RASCUNHO, nenhuma integracao ao jogo master.**

Continua a PR #115 da traducao, sem alterar o codigo da M8,
as otimizacoes experimentais ou a ROM inglesa. A engine continua
fixada em PKMN-World/15d3888b0d81322a04d3c71b0bce18948761ee44
na compilacao temporaria ARM/GBA de CI.

## Novo trabalho da etapa 10

**117 dialogos ja existentes foram revisados e reescritos
individualmente em 7 arquivos de mapa**. A contagem foi feita por
comparacao exata de cada label com a etapa 9; rotulos inalterados
nao contam.

- Sootopolis Gym (28): JUAN, RAINBADGE, WATERFALL, treinadores,
  quebra-cabeca, resultados e revanche;
- Viridian Gym (18): GIOVANNI, fim da EQUIPE ROCKET, treinadores,
  TM26 e revanche;
- Mossdeep Space Center (37): lancamentos, pesquisadores,
  STEVEN e cientistas, combustivel e invasões de NPCs;
- Mt. Chimney e estacao de teleferico (34): METEORITE, plano
  MAGMA, TRABITHA/TABITHA, interacoes e rematches.

Os dados realmente modificados estao em
`ptbr_auto_review_002.json` e `ptbr_auto_review_016.json`.
O manifesto `ptbr_reviewed_stage10.json` registra os 117 nomes
de simbolo, com a origem de cada um.

## Balanco verificavel dos 5.200 rascunhos

- Revisao humana original, etapa 7: **210**.
- Continuacao, etapa 8: **239**.
- Continuacao, etapa 9: **328**.
- **Esta etapa 10: 117**.
- Total revisado individualmente: **894 / 5.200**.
- Ainda requer revisao linguistica: **4.306**.
- Havia ainda **1.587 entradas inicialmente manuais**, registradas
  separadamente; a soma de 6.787 entradas no tradutor NAO
  equivale a um jogo com 100% de localizacao ou dialogos aprovados.

## Testes

- Politica sem acentos/cedilha nos novos textos; fonte original ASCII.
- Nomes de especies, golpes, habilidades e itens preservados.
- Macros e controles script GBA mantidos exatos por simbolo
  (`{PLAYER}`, `{STR_VAR_1}`, `{KUN}`, `\\p`, etc.).
- Para esta revisao, nenhuma fala excede a heuristica
  de 35 caracteres visiveis por linha, mas isto NAO substitui
  medicao da largura em pixels no mGBA.
- `audit_ptbr_draft_quality.py` exige registro sem sobreposicao
  as etapas 7/8/9, contagem exata de 117, ausencia de grafia
  PT-PT identificada, macros coladas, ingles residual e overflow.
- CI real: testes unitarios, aplicar no checkout World fixado,
  compilar .gba ARM, make validate e suite headless mGBA;
  status apenas confirmado apos retorno do workflow.

**Limitacao importante:** a pipeline de PT-BR historica ainda usa
`apply_grass_only.py`. Nao substituir o jogo M9 com encontro
selvagem visivel. A integracao do patch linguistico com a base
moderna precisa ser realizada separadamente e testada.

**Nao mesclar nem declarar traducao integral neste estado.**
