# Grand World GBA — traducao PT-BR, revisao humana etapa 11

**31/10/2026. Status: desenvolvimento isolado; sem merge na M8/M9.**
Branch filha da PR #116; preserva a ROM inglesa, o codigo original,
sprites, encontros selvagens visiveis e arquivos de saves.

## Revisao entregue

**170 falas diferentes foram realmente reescritas**, comparadas
simbolo por simbolo com a branch da etapa 10. Foram modificados
**26 arquivos de mapas** no manifesto PT-BR
`tools/grandworld/ptbr_auto_review_016.json`.

Locais revisados:

- Mt. Moon (1F/B2F): exploracao, TEAM ROCKET, encontro com
  fosseis, DOME FOSSIL, HELIX FOSSIL e seus eventos;
- Mt. Ember: exploradores, equipes e encontros no vulcao;
- Mt. Pyre (1F–6F, summit): exploracao, encontros, lembrancas
  dos POKEMON que partiram e a historia dos tres POKEMON ancestrais
  de HOENN;
- Mt. Mortar: POKEMANIACS, professor de KARATE e premio do desafio;
- Meteor Falls: dialogos de revanche, POKENAV, STEVEN;
- Mossdeep: SUPER ROD, casa de STEVEN, cientistas e explicacoes
  sobre agua/mar, itens e habilidades;
- Mauville: quatro instrucoes das BIKES, Game Corner,
  escolhas de premios e dialogos do visitante em 3 contra 3.

A contagem exclui explicitamente duas falas que, depois da revisao,
ficaram iguais ao texto anterior; elas NAO foram contabilizadas como
modificadas. Cada simbolo modificado aparece em
`tools/grandworld/ptbr_reviewed_stage11.json`.

## Estado acumulado dos rascunhos

| Etapa de revisao | Entradas |
| --- | ---: |
| Etapa 7 | 210 |
| Etapa 8 | 239 |
| Etapa 9 | 328 |
| Etapa 10 | 117 |
| **Etapa 11** | **170** |
| **Total de rascunhos revisados** | **1.064 / 5.200** |
| **Rascunhos ainda sem revisao individual** | **4.136** |

Havia ainda 1.587 registros de traducao inicialmente manuais.
O conjunto de 6.787 entradas processadas no pipeline nao
representa 100% da cobertura de todos os textos do jogo, muito
menos de uma ROM homologada. Textos de HUD, menus C e imagens
precisam de auditoria de cobertura.

## Preservacao e criterio tecnico

- Sem acentos nem cedilha no novo conteudo de jogo.
- Control sequences `\\n`, `\\l`, `\\p`, `$` mantidas;
  todos os nomes de macros dinâmicas preservados exatamente
  pelo inventario original (`{PLAYER}`, `{POKEBLOCK}`,
  `{STR_VAR_1}` etc).
- A verificacao de textos nao permite variaveis grudadas em
  palavras, portugues europeu sinalizado, ingles residual e
  linhas que extrapolem a heuristica de 35 caracteres.
- `audit_ptbr_draft_quality.py` exige que cada registro da etapa 11
  esteja presente, nao se sobreponha as etapas 7–10 e tenha
  texto bem-formado. Os testes de unidade validam
  1.064/5.200 e 4.136 rascunhos ainda nao revisados.
- Workflow CI valida tradutor, compilacao real ARM/GBA e
  suite de gameplay mGBA, sujeito ao resultado verificado da CI.

**Nao declarar 100%. Nao integrar `apply_grass_only.py`
com o M9 atual de encontros visiveis. Nao mesclar na M8
sem branch propria de integracao e regressao.**
