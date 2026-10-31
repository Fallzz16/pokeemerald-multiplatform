# Grand World GBA — PT-BR etapa 12 (31/10/2026)

**Status: alteracoes de traducao em branch experimental, NAO uma ROM
PT-BR 100% pronta para distribuicao.**

Continua diretamente a etapa 11/PR #117. Os manifests de traducao sao
aplicados a uma copia descartavel do PKMN-World pinada pelo workflow,
sem tocar na M8 estavel, na ROM inglesa nem no sistema moderno de
encontros selvagens visiveis.

## Trabalho realizado

**330 entradas individuais realmente alteradas** em **39 arquivos de
script** de mapas. A contagem foi obtida comparando simbolo e vetor
de strings do manifesto da etapa 11 com a etapa 12 (nao contabiliza
rascunhos inalterados). O registro exato de cada rotulo esta em
`tools/grandworld/ptbr_reviewed_stage12.json`.

Locais e conteudos trabalhados:

- National Park (Johto), Farol de Olivine e AMPHY/JASMINE, porto
  S.S. AQUA, trocas de Olivine e GOOD ROD;
- Pallet Town, casa do rival e afinidade com o POKEMON;
- Petalburg Woods, encontro com funcionarios e itens ocultos;
- Kanto Pokemon Tower, andares 1F–7F, confrontos Rocket e
  dialogos do rival;
- One Island, Celio, ligacao PC Kanto/Hoenn, SAPPHIRE,
  TRI-PASS, Ember Spa, casas e treinadores da Kindle Road;
- Cinnabar Pokemon Mansion e diarios da descoberta de MEW/MEWTWO;
- Rock Tunnel (1F/B1F), treinadores, navegacao e habitats;
- Ruins of Alph, paineis UNOWN, descricoes arqueologicas,
  mensagens e puzzles;
- Rusturf Tunnel, encontro com a equipe inimiga e HM.

Os textos foram reescritos em PT-BR natural, **ASCII sem cedilha nem
acentos**, com mesmos `{PLAYER}`, `{RIVAL}`, `{STR_VAR_1}`
etc. encontrados nas falas originais. Os controles `\\n`,
`\\l`, `\\p` e o terminador `$` foram mantidos no formato
aceito pela engine; o numero de cada macro foi conferido para cada
rotulo antes de salvar o manifesto.

A auditoria local de diferencas comparou os dois shards
`ptbr_auto_review_017.json` e `ptbr_auto_review_018.json` e
identificou **nenhum conflito com registries de revisao 7–11**,
nenhuma macro faltante, controle invalido, caracter fora de ASCII,
marcador PT de Portugal sinalizado ou linha longa pela heuristica
estatica de 35 caracteres. O verificador da CI deve confirmar de
novo o mesmo resultado e ainda compilar a ROM ARM real e testar mGBA.

## Revisao acumulada de drafts

| Etapa | Entradas revisadas |
| --- | ---: |
| 7 | 210 |
| 8 | 239 |
| 9 | 328 |
| 10 | 117 |
| 11 | 170 |
| **12** | **330** |
| **Total individualmente revisado** | **1.394 / 5.200** |
| **Rascunhos aguardando revisao linguistica** | **3.806** |

As 1.587 entradas iniciais com curadoria manual do projeto
permanecem separadas dessa contagem. O tradutor configurou antes
6.787 entradas no total, mas **isso nao prova que 100% dos
textos/menus/imagens do jogo tenham sido traduzidos**.
Nem todas as falas deste lote foram inspecionadas visualmente
em tela, e uma heuristica de 35 caracteres nao equivale a largura
pixel a pixel.

## Compatibilidade / bloqueio de integracao

O fluxo historico da traducao PT-BR ainda contem
`apply_grass_only.py`, o qual conflita com o M9 atual que usa
Pokemon selvagens visiveis. **Nao mesclar a pipeline antiga
na ROM Master**, mesmo que passe em todas as suites do World.
A integracao da camada de texto ao jogo M9 precisa aplicar
somente os patches de idioma, preservar os recursos M9 e
revalidar seguidor, encontros, saves, seis protagonistas e
viagens regionais.

**Nenhuma PR mesclada automaticamente. ROM original preservada.
Nao afirmar entrega integral sem auditoria total e testes de
interface completos.**
