# M9 — Hipotese de staging dos frames comprimidos em EWRAM

**Resultado real: NAO APROVADO.** PR #111 DRAFT, sem merge e sem
qualquer alteracao da M8 ou das PRs #109/#110 homologadas.

## Objetivo e implementacao

O piloto do Groudon da PR #109 economiza 8.056 B de payload ROM sem
incremento de RAM estatica, mas cada frame LZ10 requer ate 39.136
ciclos no BIOS dentro de VBlank (benchmark PR #110). Esta hipotese
usou 4 buffers EWRAM exclusivos de 2048 B para descompactar no
agendamento do frame com LZ77UnCompWram e fazer somente CpuCopy16 no
VBlank. Se os buffers acabam ou o pedido surge em VBlank, faz
fallback para o caminho antigo BIOS LZ77UnCompVram. O script tambem
mascara o bit 0x8000 ao cancelar requests cujos tiles foram liberados.

Cada buffer foi preservado ate o consumo ou cancelamento da fila
original; nenhum sprite fonte, paleta, save, mapa, definicao ou
regiao foi alterado. Apenas a copia descartavel da World foi
modificada no CI.

## Evidencias de execucao

[GitHub Actions #41063649000](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41063649000):
o job e deliberadamente **FAILURE**, na suite direcionada de Groudon.
Compilacao ARM/GBA real, teste de memoria e 18/18 Route 29 passaram;
9 testes anteriores de Groudon (pixels, 16 leituras de OBJ VRAM,
animacao, screenshot e sem crash) passaram. Novas verificacoes
de staging: **1/3 PASS**; portanto **10/12 PASS**, PR reprovada.

| Medida verificada | Valor |
| --- | ---: |
| Bytes ROM payload poupados frente ao World baseline | 7.896 B |
| Aumento de EWRAM estatica | **8.208 B** |
| Aumento de IWRAM estatica | 0 B |
| EWRAM estatica restante estimada | 18.816 B |
| Requests LZ10 executados antecipadamente em WRAM | 32 |
| Requests que precisaram fallback do BIOS em VRAM | **187** |
| Requests originados dentro do VBlank | **187** |
| Total requests Groudon amostrados | **219** |
| Participacao dos fallbacks (187/219) | **85,4%** |
| Testes Route29/OWE/follower/batalha | 18/18 PASS |
| Testes Groudon total, incluindo novos criterios | **10/12 FAIL** |

O resultado demonstra o problema de arquitetura: no campo a maioria
dos pedidos `RequestSpriteFrameImageCopy` nasce no proprio
VBlank; simplesmente mover a descompressao para o lugar onde o request
e enfileirado **NAO** retira seu custo do VBlank. Pior: +8.208 B de
memoria persistente custa mais memoria do que o ganho de 7.896 B no
payload da ROM nessa unica especie. Nao sugerir essa mudanca para
a ROM Master nem ignorar as duas falhas da suite.

### Conclusao / alternativas

1. **Prioridade:** testar um descompactador mais rapido dentro da
   propria janela ja existente com codificacao compativel e medicao
   direta do ciclo em ARM/GBA, comparando BIOS vs LZ4 ou ARM LZ77.
2. Outra alternativa exige reorganizar o agendamento das animacoes
   *antes* do VBlank, com prova de integridade da fila, interrupcoes
   e buffers; nao basta mover a mesma chamada C para outra funcao.
3. Ampliar apenas depois de teste com varios sprites 64x64,
   mapas densos, Surf, saves antigos e medicao real de VBlank total.
4. O erro experimental nao cancela a [PR #109](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/109)
   nem seus **8.056 B economizados e pixels corretos no mGBA**.
   A [PR #110](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/110)
   continua como evidencia do custo de 39.136 ciclos.

**Status de merge: bloqueado.**
