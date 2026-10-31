# Grand World GBA — PT-BR etapa 15

**31/10/2026 — revisao humana em branch experimental, ainda sem release.**

Continua diretamente a etapa 14/PR #120. A M8 estavel,
a ROM inglesa, os saves e o M9 com Pokemon selvagens visiveis
nao foram alterados. O motor fixado continua sendo
PKMN-World @ 15d3888b0d81322a04d3c71b0bce18948761ee44
no pipeline de compilacao PT-BR.

## Entrega concreta

**154 textos modificados individualmente em 20 arquivos de mapa**
da parte das Ilhas Sevii, registrados por simbolo no arquivo
`tools/grandworld/ptbr_reviewed_stage15.json`. Foram editadas
155 entradas, mas uma ficou com a mesma string anterior e
NAO entrou no registro de "novo texto revisado".

Areas trabalhadas:

- **Seven Island:** ilha principal, mestre de SWORDS DANCE, casa
  de batalhas 3-contra-3, Pokemon Center, Sevault Canyon
  (entrada, trilha, casa e TANOBY KEY), TANOBY RUINS
  e TRAINER TOWER.
- **Six Island:** DOTTED HOLE/SAPPHIRE, ilha, Pattern Bush e
  seus treinadores, OUTCAST ISLAND, RUIN VALLEY e mensagens
  de exploracao, WATER PATH e casa do HERACROSS medido,
  Pokemon Center e NPCs.
- Todas as ocorrencias dinamicas de `{PLAYER}`,
  `{STR_VAR_1}`, `{STR_VAR_2}` e `{STR_VAR_3}`
  contidas nos simbolos editados foram mantidas,
  inclusive em frases de recompensa e medicao.

### Progresso da revisao dos 5.200 rascunhos

| Etapa | Revisoes novas |
| --- | ---: |
| 7 | 210 |
| 8 | 239 |
| 9 | 328 |
| 10 | 117 |
| 11 | 170 |
| 12 | 330 |
| 13 | 124 |
| 14 | 165 |
| **15** | **154** |
| **Revisados, acumulado** | **1.837 de 5.200** |
| **Ainda exigem revisao individual** | **3.363** |

Existem ainda 1.587 entradas iniciais manuais na configuracao
anterior. A soma de 6.787 textos registrados na pipeline NAO
demonstra cobertura integral da ROM, pois menus C, interface,
strings dinamicas e graficos com texto ainda precisam ser
inventariados e validados.

## Checagens e limites

- ASCII simples sem cedilha ou acentos, como solicitado.
- Prefixos, tokens dinamicos, controles `\\n`, `\\l`, `\\p`
  e terminador `$` preservados em cada label.
- Nenhuma sobreposicao com manifests de revisao 7–14.
- Nenhum placeholder colado, marcador detectado de portugues
  europeu ou ingles residual, nem linha acima da heuristica
  de 35 caracteres nos 154 textos novos.
- Auditoria Python agora inclui o `ptbr_reviewed_stage15.json`;
  teste e CI exigem 1.837 revisados/3.363 pendentes.
- O workflow pode compilar ROM .gba ARM, executar validacoes
  e 51 suites mGBA. O resultado desta etapa nao deve ser
  considerado confirmado antes da execucao terminar.

A heuristica de comprimento de linha nao corresponde a largura
da fonte real em pixels: e necessario testar visualmente as
variaveis de Pokemon/nome de jogador.

**Nao mesclar com a M8 nem com a M9 sem extrair a camada
de texto do pipeline legado.** Em particular,
`apply_grass_only.py` da traducao historica nao deve
desativar os encontros selvagens visiveis do jogo atual.

**Nao afirmar 100% de localizacao, nao distribuir ROM.**
