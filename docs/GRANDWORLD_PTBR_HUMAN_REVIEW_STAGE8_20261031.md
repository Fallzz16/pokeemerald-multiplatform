# Grand World GBA — revisao humana PT-BR, etapa 8 (31/10/2026)

**Estado: em andamento, NAO e traducao completa nem release.**
Branch filha de `feature/grandworld-ptbr-stage1-20261025` (PR #77).
O codigo M8 e a ROM inglesa nao foram alterados. A traducao e aplicada
em checkout World descartavel no commit
`15d3888b0d81322a04d3c71b0bce18948761ee44` pelas ferramentas
de localizacao ja existentes.

## Avanco real e como foi medido

O projeto ja possuia **1.587** entradas originais revistas/manualizadas
e **5.200** rascunhos assistidos de traducao, aplicados com verificacao
de macros. "6.787 entradas aplicadas" **NAO significa** 6.787 traducoes
humanas aprovadas ou 100% do texto do jogo.

- Revisao humana de auto-drafts anteriormente concluida: **210** entradas
  da etapa 7.
- **239 entradas adicionais** tiveram o texto alterado por revisao
  individual nesta etapa, listadas exaustivamente em
  `tools/grandworld/ptbr_reviewed_stage8.json` com seus nomes exatos.
- Total dos rascunhos assistidos agora revisados humanamente:
  **449 de 5.200**.
- Rascunhos assistidos **ainda pendentes de revisao humana: 4.751**.
- Numero total dos arquivos de mapa cujo rascunho foi alterado nesta
  etapa: **38**. Os rascunhos inalterados nao entram na contagem,
  mesmo que tenham sido inspecionados.

### Areas revisadas nesta etapa

1. Johto: subterraneo de GOLDENROD, cabeleireiros de POKEMON, ICE PATH,
   ILEX FOREST, INDIGO PLATEAU, LIGA POKEMON e parte de VICTORY ROAD.
2. Hoenn: GRANITE CAVE, JAGGED PASS, concursos, lojas, ferry e hotel de
   LILYCOVE, esconderijo da EQUIPE MAGMA em todos os andares.
3. Johto: esconderijo ROCKET em MAHOGANY, falas de LANCE, PETREL,
   ARIANA, portas com duas senhas e cientistas.

Os textos foram reescritos em PT-BR de forma contextual, sem mudar
nomes de especies, movimentos, habilidades, itens e personagens fora
da politica previamente definida. Em casos de comportamento do jogo,
os textos ingleses originais foram conferidos contra a World pinada.
A fonte `LanceWhirlpool` por exemplo fala de `HM DIVE` nessa engine
especifica: nao "corrigir" o nome com base em outro jogo sem antes
corrigir/validar a mecanica.

## Controles e validacoes

- Nenhuma letra acentuada nem cedilha nos novos dialogos do jogo;
  todas as 239 entradas usam ASCII comum.
- Preserva a contagem de `{PLAYER}`, `{STR_VAR_1}`,
  `{POKEBLOCK}` e quaisquer outros placeholders.
- Preserva controles reais da engine (\n, \p, \l, terminador `$`),
  e rejeita texto que substitua macros por prosa.
- Nenhuma linha visualmente renderizavel no lote revisado ultrapassa
  **35 caracteres equivalentes** na heuristica automatica. Isso
  nao substitui teste visual do tamanho em pixels e largura real da fonte.
- `audit_ptbr_draft_quality.py` agora exige que todos os textos
  registrados como revisados na etapa 8 estejam em ASCII, terminem
  em `$` e nao tenham sinais de portugues europeu, ingles residual,
  macro grudada nem linhas excessivas.
- A heuristica distingue corretamente o plural legitimo
  `{POKEBLOCK}S` do erro `{PLAYER}recebeu`.
- Os testes de unidade foram atualizados para rejeitar a contagem
  errada de revisoes; CI exige **449 revisados**, **239 nesta etapa**,
  e **4.751 pendentes**.
- O tradutor continua a validar os anchors exatos dos textos no codigo
  original e *planejar todo o patch antes de escrever*; qualquer drift
  bloqueia a alteracao e preserva os arquivos originais.

## Limitacoes e plano realista para finalizar

**Nao declarar o jogo inteiro traduzido.** A falta de revisao humana de
4.751 entradas e os textos pendentes fora dos manifests impede afirmar
100% de cobertura. O inventario de `audit_ptbr_coverage.py` inclui
apenas textos estaticos de mapas, data/text e determinados C; existem
textos dinamicos, graficos de letras e outras C sources fora do escopo.

Antes de liberar a ROM Master PT-BR, ainda sao obrigatorios:

1. revisar os 4.751 rascunhos, corrigir macros anormais, PT-PT e
   termos que mudem significado; continuar por manifestos menores;
2. revisar os textos que permanecem ingleses e ampliar inventario
   para todos os C sources e texturas/menus com letras;
3. passar compilacao ARM/GBA e todas as suites com a ROM PT-BR
   exata do commit, incluindo boot, save/continue e seis herois;
4. validar caixas de dialogo reais no mGBA, incluindo BIRCH,
   interface, lojas, ligas e falas com parametros dinamicos;
5. conciliar esta branch de traducao com a **base atual de encontros
   visiveis**, pois o pipeline historico da PR #77 ainda traz
   `apply_grass_only.py`. Nao integrar esse comportamento ao ramo
   master moderno que exige encontros visiveis. Adotar uma branch de
   integracao separada somente apos o patch linguistico passar nos
   testes e incorporar OWE sem alterar a M8 estavel.

**Nao distribuir automaticamente ROM. Nenhum merge realizado.**
