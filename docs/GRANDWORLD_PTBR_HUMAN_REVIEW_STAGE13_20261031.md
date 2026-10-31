# Grand World GBA — traducao PT-BR, etapa 13

**Data: 31/10/2026. Status: PR isolada, NAO homologada para a ROM Master.**

Este lote continua diretamente a etapa 12, que deriva da traducao
existente da PR #77, sem alterar a M8 estavel, sprites originais,
RAM do GBA, ROM inglesa, encontros selvagens visiveis ou saves.

## Conteudo revisto nesta rodada

**124 entradas individuais realmente modificadas em 17 arquivos de
mapa**, obtidas por comparacao de cada simbolo/array com o manifesto
da etapa 12. Textos inalterados (tres durante a edicao) NAO foram
contados como novas revisoes. Registro detalhado:
`tools/grandworld/ptbr_reviewed_stage13.json`.

- Silph Co. Kanto, segundo ao decimo primeiro andar: 84 entradas
  trabalhadas sobre funcionarios, GIOVANNI, Equipe Rocket, rival,
  recebimento de LAPRAS, informacoes dos teletransportes e
  pistas do edificio;
- S.S. AQUA Johto: 1F, B1F e sala do capitao: 27 entradas,
  marujos, ajuda com passageira desaparecida, cabine e descanso;
- Seafloor Cavern Hoenn: 15 entradas trabalhadas sobre GRUNTS,
  invasao do submarino, ARCHIE e RED ORB.

As contagens de "trabalhadas" incluem poucas falas reescritas para
a mesma string ja presente; a contagem distinta provada por diff
e **124**, nao a soma nominal de entradas inspecionadas.

## Estado cumulativo dos 5.200 rascunhos

| Fase | Revisados |
| --- | ---: |
| Estagio 7 | 210 |
| Estagio 8 | 239 |
| Estagio 9 | 328 |
| Estagio 10 | 117 |
| Estagio 11 | 170 |
| Estagio 12 | 330 |
| **Estagio 13** | **124** |
| **Total com revisao linguistica individual** | **1.518 / 5.200** |
| **Ainda pendentes de revisao individual** | **3.682** |

A traducao original tinha mais 1.587 entradas inicialmente manuais,
mantidas fora desse subtotal. **6.787 entradas aplicadas no pipeline
nao significam 100% da traducao do jogo inteiro**; ha textos dinamicos,
menus C e imagens que nao constam do atual inventario.

## Verificacoes

- Sem cedilhas nem acentos nos novos textos (ASCII), conforme
  convencao do projeto.
- Nomes de simbolo originais e contagem de macros dinamicas
  `{PLAYER}`, `{RIVAL}`, `{STR_VAR_1}` etc preservados.
- Controles `\\n`, `\\l`, `\\p`, `$` mantidos.
- Nenhuma sobreposicao com os manifests de revisao das etapas 7–12;
  nenhuma variavel colada, ingles residual obvio, marcador de
  portugues europeu ou linha acima da heuristica de 35 caracteres.
- Auditoria `audit_ptbr_draft_quality.py` passa a exigir 124 novas
  entradas e soma 1.518/5.200; workflow de compilacao ARM/GBA e
  testes mGBA precisara confirmar.
- A heuristica de linhas nao substitui teste real de overflow de
  fonte, e as 51 suites existentes nao provam a leitura de
  cada caixa de dialogo.

## Proxima integracao

O tradutor historico ainda traz `apply_grass_only.py`, incompativel
com o objetivo atual M9 de encontros visiveis. **Nao mesclar
esse runtime legado no jogo master.** Deve-se aplicar apenas
os dados da traducao ao motor atual e repetir QA de
seguidores, encontros visiveis, saves, mapa e personagens.

**Nao fazer merge automatico; nao afirmar 100% de PT-BR.**
