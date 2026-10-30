# GBA M9 — Stress real das copias de sprites em VBlank

**Resultado:** CI **SUCCESS**, experimento validado como diagnostico, **NAO
APROVADO PARA MERGE**. Branch e PR #113 em rascunho; M8 intacta.

Fonte de evidencia: [GitHub Actions #41070728291](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41070728291)
e [artefato 12984274158](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41070728291/artifacts/12984274158).
ROM ARM/GBA verdadeira, headless mGBA nativo, **18/18 testes de
Route29** e **19/19 testes Groudon** aprovados.

## Carga cronometrada no mGBA

| Chamadas LZ10 ARM 2KiB na mesma fila de VBlank | Amostras | Pico de ciclos | Lotes acima de 83.776 | VRAM OBJ |
| --- | ---: | ---: | ---: | --- |
| 1 (normal) | 221 | 29.107 | 0 | correto |
| 2 | 133 | **48.742** | 0 | 16/16 correto |
| 3 | 135 | **69.015** | 0 | 16/16 correto |
| 4 | 135 | **91.020** | **135 de 135** | 16/16 correto |

Em todos os 135 lotes do nivel 4 houve cruzamento da janela VBlank.
Os picos incluem decompressor ARM mais as copias de sprite *que
conseguimos cronometrar* dentro da fila, mas nao OAM, DMA, audio nem
outros handlers. Ha 15 copias normais sem medicao por timers ocupados;
foram preservados sem sobrescrever os donos do Timer2/3. O decoder
teve **0 conflitos reais**. Media de 221 chamadas individuais de
Groudon normal: **21.589 ciclos**; pico individual **21.881**.

**Metodo preciso:** a suite repete 2 a 4 descompressoes genuinas para
os **mesmos tiles OBJ legalmente alocados** do Groudon dentro de UMA
chamada a `ProcessSpriteCopyRequests`. O CPU/GBA e real; isto **NAO
equivale a 2–4 Groudon visiveis**, nem verifica multiplos destinos de
VRAM ou alocacao de paletas simultaneas. Nenhum save, sprite-fonte,
mapa ou configuracao do jogo foi alterado.

### Memoria

Diferencas da ROM experimental versus baseline World, medidas no linker:
**7.024 bytes economizados em payload ROM**, **+100 B EWRAM** de
telemetria e **+552 B IWRAM** para o ARM otimizado. Esses valores sao
de uma build de testes, nao de producao. Comparar separadamente com
PR #109 BIOS (8.056 B economizados com +0 RAM) e PR #112 (7.360 B
economizados, +16B EWRAM para perfil e +552B IWRAM).

### Decisao

- **Quatro decodes grandes por VBlank reprovados.** Houve estouro
  observado, mesmo sem todas as tarefas do VBlank contabilizadas.
- **Tres decodes nao sao automaticamente seguros**, pois sobraram
  apenas 14.761 ciclos para outros trabalhos no pico observado.
- Duas chamadas ficaram abaixo do limite, mas nao sao autorizacao
  de habilitacao geral sem teste de VBlank agregado, FPS, audio,
  varios sprites visiveis e hardware.
- Nao postergar copias de sprite entre frames sem gerenciar *lifetime*
  de sprites, memoria OBJ realocada e requests obsoletos.
- Proximo passo obrigatorio: validar simultaneidade de dois ou mais
  objetos graficos grandes reais e ocupacao de VRAM, antes de
  expandir compressao para outras especies.

**NENHUMA PR MESCLADA. M8 ESTAVEL PRESERVADA.**
