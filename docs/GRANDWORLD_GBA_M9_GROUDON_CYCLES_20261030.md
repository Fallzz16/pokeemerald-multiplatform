# M9 GBA — Benchmark real de ciclos para Groudon LZ10 por frame

Status: **PR #110 DRAFT / SOMENTE DIAGNÓSTICO. NÃO MESCLAR.**
Derivado da PR #109 visualmente homologada; M8 estável intacta.
World pin: `15d3888b0d81322a04d3c71b0bce18948761ee44`.

## Resultado do GitHub Actions

[Run #41060393430](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41060393430): **SUCCESS**.
Duas compilações ARM/GBA, teste existente de encontros visíveis
**18/18** e teste direcionado de Groudon seguidor/VRAM **12/12**.
[Evidências de log/JSON/screenshot, sem ROM nem saves](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41060393430/artifacts/12979071951).

| Medida no mGBA com hardware Timer2/3 | Resultado |
| --- | ---: |
| Amostras de descompressão BIOS LZ10 de 2.048 bytes | 221 |
| Pico de ciclos de uma chamada | **39.136** |
| Média inteira por chamada | **38.626** |
| Soma de ciclos | 8.536.433 |
| Conflitos com timers ocupados | **0** |
| Ciclos de um VBlank inteiro (68 scanlines × 1.232) | 83.776 |
| Percentual máximo do VBlank para **uma chamada** | **46,72%** |
| Testes Groudon de animação e pixels OBJ VRAM | **12/12 PASS** |
| Testes OWE Route29 com follower e batalha real | **18/18 PASS** |

O método usa `CycleCountStart()` e `CycleCountEnd()` *já presentes*
no `global.h` da World. O código de medição entra SOMENTE em uma cópia
descartável da engine durante o CI. Verifica que Timer2/3 não estavam
ativos antes de iniciar, e conta conflitos; descomprime normalmente se
ocupados. O script anexa quatro `u32` de diagnóstico, somando **16 B
EWRAM estática temporária**, NÃO presentes na versão de produção.

O perfil deste CI fica com **7.928 B** de redução de payload ROM frente
ao baseline, e **+16 B EWRAM estática** devido aos contadores. Esses
números NÃO substituem o ganho real do piloto de produção da
[PR #109](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/109):
**8.056 B de ROM economizados, 0 B de EWRAM/IWRAM adicional**.

## Decisão sobre desempenho

- Uma chamada que consome 39.136 ciclos é menos que 83.776 ciclos
  da janela VBlank, mas toma **quase metade dela**.
- Duas chamadas semelhantes na **mesma janela** custariam aproximadamente
  78.272 ciclos (~93,4%), deixando ~5.504 ciclos para **todo o resto**.
  Ocorre risco de atraso gráfico, pois sprites e paletas adicionais
  também usam VRAM, OAM e DMA no VBlank.
- Três chamadas com o pico equivaleriam a ~117.408 ciclos,
  excedendo o intervalo em ~33.632 ciclos.
- Isto é uma **projeção aditiva**, não um stress test real com dois/três
  Groudon simultâneos. Não afirmar queda de FPS ou glitches observados.
- O teste de timer mede só a chamada BIOS LZ10 e o overhead mínimo da
  instrumentação. NÃO mede uso agregado de VBlank, distribuição de
  cópias por VBlank, latência de áudio, FPS, RAM dinâmica, hardware físico,
  saves antigos, densidade de NPCs ou Surf.

## Próximos experimentos, sem habilitar em massa

1. Medir impacto de duas/três descompressões reais em um único VBlank,
   com contador por `ProcessSpriteCopyRequests()` e benchmark nativo.
2. Preferir tentativa de decoder **mais rápido** para 2KiB ou
   descompressão antes de VBlank em buffer WRAM temporário com fila de
   cópia segura e limites explícitos de RAM. NUNCA reutilizar um buffer
   de staging antes de a fila transferir os pixels.
3. Avaliar espécies menores 32×32 (512B/frame), cujas descompressões
   tendem a ser mais baratas mas exigem **medição real**, não projeção
   linear dos 2KiB.
4. Repetir testes de pixels e frames, 18/18 OWE, mapas densos, Surf,
   reinício e saves antigos antes de promover uma estratégia.

## Benchmark alternativo para pesquisa

[GBA-compress](https://github.com/HorstBaerbel/GBA-compress) oferece
LZ4 e LZ77 com descompactadores ARM e afirma melhor velocidade LZ4
em um corpus próprio. São **benchmarks de outra engine**, não uma
medição do Grand World. Manter um A/B medido e reversível antes de
importar um decoder de terceiros (respeitar licença MIT e proveniência).

**Conclusão:** o Groudon LZ10 agora está comprovadamente funcional,
com economia ROM real, mas **não escalar indiscriminadamente** enquanto
o custo de VBlank não for reduzido. PR #109/110 continuam DRAFT.
