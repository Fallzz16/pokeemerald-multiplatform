# Grand World GBA PT-BR — revisao humana, etapa 9

**Data: 31/10/2026. Status: tradutor em desenvolvimento, sem release.**

Branch filha de `feature/grandworld-ptbr-human-review-stage8-20261031`,
PR #114. A M8 estavel, a ROM inglesa e o projeto Web foram preservados;
nenhuma branch previa foi mesclada nem substituida. Os manifests continuam
sendo aplicados em um checkout temporario do PKMN-World pinado no CI.

## Entregas desta rodada

- **328 entradas de texto foram reescritas e revisadas individualmente**
  nesta etapa, contadas por `(arquivo, simbolo)` comparando o manifesto
  anterior com o atual; rascunhos iguais nao contam.
- **41 arquivos de mapas** alterados em
  `ptbr_auto_review_002.json`, `ptbr_auto_review_014.json`
  e `ptbr_auto_review_015.json`.
- Ginasios de **Mossdeep, Olivine (Jasmine), Saffron (Sabrina)
  e Vermilion (Lt. Surge)**; batalha, insigneas, TMs, NPCs e revanche.
- **Victory Road Johto** B1F/B2F, **Lake of Rage**, encontros com
  Lance, pescadores e recompensas, casas do lago.
- **Lavaridge**: EGG, fontes termais, HERB SHOP, POKEMON CENTER.
- **Lavender**: memoriais POKEMON, Namerater, casa de Mr. Fuji e
  POKE FLUTE; cinemática por texto preservada.
- **Lilycove**: 32 falas completas do Fan Club com variaveis dinamicas
  de jogador e treinadores, Museu (36 entradas), Move Deleter,
  departamento e demais textos de NPC revisados.
- **Littleroot**: dialogos de casa do protagonista, rival e introducao.
- **Mahogany e Mauville**: lojas, encontros de Lance, centros
  POKEMON, POKENAV, bicicletas e comandos de orientacao.
- **Cinnabar**: 17 textos de laboratorio, reviver fosseis, METRONOME,
  Pokemon cientificos e dinamicas {STR_VAR_*}.
- **Kanto Team Rocket**: 19 textos de esconderijo B1F–B4F,
  incluindo Giovanni e elevador.

O novo arquivo `tools/grandworld/ptbr_reviewed_stage9.json` registra
cada simbolo realmente revisado e a fonte do shard, para evitar afirmar
que rascunhos nao inspecionados foram revisados.

### Contagem real

| Natureza do dado | Entradas |
| --- | ---: |
| Rascunhos de traducao automatica originais | 5.200 |
| Revisados individualmente na etapa 7 | 210 |
| Revisados individualmente na etapa 8 | 239 |
| **Novos revisados nesta etapa 9** | **328** |
| **Revisados acumulados nos rascunhos** | **777** |
| **Rascunhos pendentes de revisao individual** | **4.423** |
| Traducoes manuais/configuradas anteriormente | 1.587 |
| Entradas aplicadas pelo tradutor anterior | 6.787 |

Os 6.787 registros aplicados **NAO equivalem a 100% do jogo traduzido**
e nao sao 6.787 dialogos certificados como bem escritos.
Ainda existem textos fora do escopo da cobertura atual
(C adicionais, interfaces dinamicas e arte com textos).

### Guardrails tecnicos

- Mantem todos os tokens de controle e variaveis de cada entrada
  (`{PLAYER}`, `{KUN}`, `{STR_VAR_1}`, `{PLAY_BGM}`,
  `{MUS_RG_ENCOUNTER_GYM_LEADER}`, `{FONT_NORMAL}` etc.).
- Mantem `$` terminal, controles de paragrafo/linha
  (`\\n`, `\\l`, `\\p`) e ASCII sem acentos nem cedilha.
- Nenhuma das **328 novas revisoes** possui warnings estaticos
  de PT europeu, ingles residual, variaveis coladas, grafia de
  movimento invertida ou linhas acima da heuristica de 35 caracteres.
- Para evitar falso positivo, `audit_ptbr_draft_quality.py`
  nao conta comandos nao visiveis de BGM ou mudanca de fonte como
  caracteres impressos no dialogo.
- A CI foi atualizada para exigir contagem exata de revisoes
  e rejeitar erros dos novos textos em todos os 21 shards,
  alem de preservar compilacao ARM/GBA, boot/titulo e 51 suites mGBA.

**Limites:** a contagem de caracteres nao e uma medicao real
de largura de pixels; e necessario revisar algumas caixas com
conteudo dinamico no emulador. Os testes existentes apenas garantem
que a ROM e os eventos rodem, nao revisam visualmente cada fala.

### Critico para integracao

O workflow de localizacao herdado da PR #77 ainda monta um perfil
`apply_grass_only.py`, que nao deve ser aplicado ao Grand World M9
moderno com encontros de Pokemon visiveis. Esta etapa apenas melhora
os dados da traducao; a integracao com o runtime atualizado deve ser
uma PR propria, preservando encontros visiveis, seguidores e saves.

**Nao fazer merge automatico. Nao liberar a ROM como traducao integral
ate concluir a revisao, auditoria de cobertura e QA no M9 atual.**
