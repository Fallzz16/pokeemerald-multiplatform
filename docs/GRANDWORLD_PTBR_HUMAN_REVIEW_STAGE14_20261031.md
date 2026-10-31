# Grand World GBA — revisao PT-BR etapa 14

**Data: 31/10/2026. Estado: em revisao, NAO e um release completo.**

Branch experimental filha da etapa 13 (PR #119). Os manifests permanecem
isolados da M8 estavel e do motor M9 com encontros de Pokemon visiveis.
Nenhum codigo da ROM inglesa, save, sprites ou gameplay foi alterado.

## Entregas concretas

Foram **165 entradas individuais de dialogo efetivamente modificadas** em
**22 arquivos de mapas**, comparadas simbolo a simbolo com a etapa 13.
As falas editadas que ficaram identicas ao texto anterior nao contam.

Os nomes exatos constam do arquivo
`tools/grandworld/ptbr_reviewed_stage14.json`.

### Regioes e eventos

- **Kanto, Saffron City**: 30 falas inteiras do Trainer Fan Club, com
  todas as ocorrencias de `{PLAYER}` e `{STR_VAR_1}` preservadas,
  mais o DOJO, COPYCAT, MR. PSYCHIC e NPCs durante a ocupacao Rocket.
- **Hoenn, Slateport**: museu oceanico 1F/2F, invasao da EQUIPE AQUA,
  busca pelas pecas do navio e sala de exposicoes (sedimentos, areia,
  fosseis, mares profundos); estaleiro de STERN.
- **Johto, SLOWPOKE WELL**: confrontos Rocket, PROTON, retirada das
  caudas dos SLOWPOKE e dialogos de eventos.
- **Johto, SPROUT TOWER**: 1F, 2F, 3F, varios SAGE, licao sobre
  cooperacao e entrega de FLASH HM.
- **Hoenn, SOOTOPOLIS**: trama central de GROUDON/KYOGRE/RAYQUAZA,
  intervencao de WALLACE, agradecimentos, habitantes e casas.
  A dinamica `{PLAYER}{KUN}` e preservada na fala de WALLACE.

### Numeros verificaveis

| Fase | Rascunhos revisados individualmente |
| --- | ---: |
| Etapa 7 | 210 |
| Etapa 8 | 239 |
| Etapa 9 | 328 |
| Etapa 10 | 117 |
| Etapa 11 | 170 |
| Etapa 12 | 330 |
| Etapa 13 | 124 |
| **Etapa 14** | **165** |
| **Total revisado** | **1.683 / 5.200** |
| **Rascunhos pendentes** | **3.517** |

Mais 1.587 entradas inicialmente manuais foram configuradas anteriormente
no pipeline; nao se confundem com revisoes dos 5.200 rascunhos.
A existencia de 6.787 entradas configuradas NAO demonstra 100% de
cobertura dos textos do jogo; HUD, menus dinamicos, texto renderizado
por C, artes e demais fontes nao cobertas continuam pendentes de
auditoria especifica.

### Verificacoes aplicadas

- ASCII sem cedilha nem acento nos textos do jogo.
- Todos os placeholders de cada entrada comparados ao texto anterior,
  incluindo contagem de repeticoes. Quatro dialogos do Fan Club
  falharam a primeira tentativa e so foram alterados depois de
  corrigir as ocorrencias dinamicas; nao houve salvamento parcial
  daquela tentativa.
- Nenhum token de evento removido; controles `\\n`, `\\p`,
  `\\l` e o terminador `$` foram conservados.
- Revisao automatica por diffs conferiu todas as 165 entradas contra
  os registros de revisao das etapas 7–13: sem sobreposicoes,
  variaveis coladas, erros de ASCII, marcadores PT-PT, residuos
  ingleses evidentes ou linhas acima do criterio estatico.
- A rotina `audit_ptbr_draft_quality.py` foi atualizada para falhar
  diante de registros incorretos da etapa 14, e os testes de unidade
  agora exigem exatamente 1.683 revisoes e 3.517 rascunhos pendentes.
- O workflow GitHub Actions deve executar testes de script,
  compilacao ARM/GBA da World pinada e 51 suites mGBA. **O
  resultado so pode ser certificado depois da conclusao da execucao.**

### Restricoes de entrega

A validacao estatica de comprimento nao corresponde a medicao de
largura de fontes em pixels. A cobertura e qualidade de cada dialogo
em tela exige um ciclo de QA visual no mGBA.

O workflow PT-BR herdado da PR #77 usa um perfil legado
`apply_grass_only.py` e **NAO deve substituir o M9 atual** com
Pokemon selvagens visiveis. A integracao ao Grand World Master deve
ser limitada aos textos e executada separadamente com testes de
encontros visiveis, seguidores, personagens e saves.

**Nao mesclar nem distribuir como traducao integral.**
