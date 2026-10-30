# M9 GBA: piloto de compressão por frame do Groudon

**Estado: experimental, PR #109 em draft; não mesclar na M8.**
Base: PR #108, que depende do diagnóstico OBJ VRAM da PR #107.
Engine World fixada em `15d3888b0d81322a04d3c71b0bce18948761ee44`.
As mudanças no código C e nos sprites são geradas **somente na cópia descartável
da engine usada pelo GitHub Actions**; a branch mantém scripts, testes e QA.

## Compilação e economia já comprovadas

[GitHub Actions #41057342617](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41057342617):
**SUCCESS**, duas compilações ARM/GBA e 18/18 checks de gameplay no mGBA.

| Medida | Resultado |
| --- | ---: |
| Groudon normal, 6 frames 64×64 em 4bpp | 12.288 bytes brutos |
| Seis arrays LZ10 separados e alinhados a 4 B | 4.152 bytes |
| Ganho bruto nos arrays antes de código | 8.136 bytes |
| **Ganho real no payload vinculado da ROM ARM** | **8.056 bytes** |
| Delta EWRAM/IWRAM estática | **0/0 bytes** |
| Frames recuperados byte a byte da ROM final | **6/6** |
| Sprite original sem compressão no ELF | **Ausente** |
| Regressão Route29 / Pokémon selvagens visíveis | **18/18 PASS** |

Baseline: SHA256
`f581ba7e6229732faa17e79a11825682861c67dcbf6ee4670dabff20dd3279ae`.
Piloto: SHA256
`6ca77d46a109d9f36f39b826623167f21e0aee8067b8d8595b39566277898971`.

## Por que a codificação é por frame, e não por folha inteira

A World usa uma lista de `SpriteFrameImage` e a função
`RequestSpriteFrameImageCopy`; cada frame do Groudon tem **2.048 bytes**,
equivalentes a **64 tiles OBJ**. Uma folha original completa possui
12.288 bytes e a expansão de toda a folha na OBJ VRAM seria incompatível
com nosso orçamento de sprites visíveis.

O patch faz `sPicTable_Groudon` apontar para seis arrays LZ10 individuais,
com o sinalizador específico `relativeFrames=2` apenas para esse caso.
A fila nativa `ProcessSpriteCopyRequests` despacha esses pedidos com
`LZ77UnCompVram` e mantém `CpuCopy16` para os sprites originais.
O gerador exige distância mínima LZ10 igual a 2, respeitando a escrita
de 16 bits na VRAM pelo BIOS. A configuração global
`OW_GFX_COMPRESS` continua **FALSE**.

## O que ainda falta provar

- Que o Groudon apareça realmente no mGBA e alterne frames sem artefatos;
- que os bytes efetivamente copiados para OBJ VRAM coincidam com os
  seis frames originais;
- tempo da descompressão dentro do VBlank, CPU, DMA e frame pacing;
- situações com múltiplos sprites 64×64 simultâneos, Surf e mapas densos;
- compatibilidade real com saves antigos (apesar do formato não alterado).

Foi adicionada a suíte
`qa/gba/GrandWorldGroudonFollowerLZ10.lua`: usa apenas Give Pokémon e
Warp oficiais da interface de debug em estado descartável, acompanha o
seguidor real em Route29, compara hashes de **2.048 bytes de OBJ VRAM**
com os frames originais, exige mais de um frame de animação, salva uma
captura e verifica ausência de crash.
[Workflow da suíte específica](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41058785637).
**O sucesso da suíte específica só deve ser declarado após o workflow
concluir em verde; a suíte anterior 18/18 não exercitava Groudon.**

## Decisão sobre rollout

Enquanto não houver confirmação visual, VRAM e de tempo por frame,
**não expandir para outras espécies**, mesmo que se economizem 8.056 B
na ROM. Se a descompressão em VBlank provocar stutter ou ultrapassar o
orçamento, testar fila amortizada e descompressão fora do VBlank antes
de promover a mudança.

Todos os dados de Pokémon, paletas, shinies, sprites-fonte, saves
existentes, mapas e a M8 ficam preservados.

## Homologacao visual definitiva do Groudon — 30/10/2026

[GitHub Actions #41058785637](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41058785637):
**SUCCESS**. Dois builds ARM/GBA, mGBA Route29 **18/18** e
mGBA seguidor Groudon **9/9**.
[Artifact de evidencias, sem cartucho nem saves](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41058785637/artifacts/12978995079).

A suite `GrandWorldGroudonFollowerLZ10` deu um Groudon pela
interface de debug original apenas numa sessao mGBA descartavel, usou
warp de debug para Route29, verificou o objeto real do seguidor de
species **383**, sprite **3** e tiles OBJ a partir do indice **36**.
Realizou **16 leituras completas de 2.048 bytes** de VRAM OBJ e todas
corresponderam a algum hash de frame de origem; observou **tres
frames diferentes (1, 3 e 5)** enquanto o jogador se movia. Foi
gerado screenshot nativo do Groudon visivel; sem crash ou alteracao
de save.

A validacao de bytes via SHA256 feita no cartucho final ja havia
aprovado seis de seis frames. A prova runtime com hashes FNV32 da
VRAM amplia a garantia, mas nao testa todos os seis frames em tela:
apenas tres apareceram nessa sequencia de passos.

**Valores reproduzidos nesta execucao: ganho real de 8.056 bytes no
payload vinculado da ROM; delta 0 B de EWRAM e 0 B de IWRAM estaticas**,
sprites OWEs e seguidor continuaram funcionando. Os 32 MiB do
arquivo .gba de cartucho preenchido nao foram reduzidos, apenas o
espaco ocupado dentro dele.

**Ainda pendente:** ciclos da BIOS LZ10 dentro do VBlank, multiplos
Groudon simultaneos, Surf e regressao de saves antigos. A
[PR #110](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/110)
mede ciclos via ferramenta nativa, em outra branch DRAFT com +16 B
temporarios de EWRAM para telemetria, sem modificar este piloto.
