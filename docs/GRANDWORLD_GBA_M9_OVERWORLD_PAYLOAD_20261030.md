# M9 — Experimento de deduplicacao e compressao de overwrite sprites na ROM real

**Status:** experimento read-only, sem economia real aplicada nem merge. Base: PR #107.
Engine PKMN-World pin: 15d3888b0d81322a04d3c71b0bce18948761ee44.
Plataforma: **ARM/Game Boy Advance**, nao PC.

## Validação completa

[GitHub Actions #41050845576](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41050845576):
**SUCCESS**. ARM/GBA compilado, testes do analisador e suite mGBA de
Pokemon visiveis **18/18 PASS**.
Codigo validado: commit `3c7d2535b411317a387b90c7664e9722d920e6f9`.
SHA256 da ROM de prova:
`f581ba7e6229732faa17e79a11825682861c67dcbf6ee4670dabff20dd3279ae`.
[Evidencias JSON/logs sem ROM nem saves](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41050845576/artifacts/12973909066).

## Achados no cartucho GBA vinculado

O scanner le `arm-none-eabi-nm -S` e os offsets do cartucho real para
comparar **bytes completos**, nao apenas nomes, PNGs de origem ou hashes.

- 1.216 simbolos `gObjectEventPic_*` efetivamente vinculados;
- 3.298.432 bytes no total nesses simbolos, sem aliases duplicados de endereco;
- dois grupos de arrays de overworld com bytes 100% identicos, mas enderecos
  distintos, potencial **MAXIMO** de 14.592 bytes brutos:
  - `gObjectEventPic_LatiasMega` e `gObjectEventPic_LatiosMega`:
    12.288 bytes duplicados;
  - `gObjectEventPic_DevonEmployee` e `gObjectEventPic_Man2`:
    2.304 bytes duplicados.

Esses sao **candidatos**, nao seguranca provada de apontar todos os assets
para um unico simbolo. Cada alias precisa preservar a identidade de forma,
tamanho, ordem dos frames, sprite palette, shiny e contratos de referencia.
A comparacao nao removeu arquivos, nao mudou linker e **economizou 0 bytes**.

## Teste LZ10 (BIOS) reversivel

Amostra determinada dos **24 maiores arrays** vinculados no ELF:

| Medida | Resultado |
| --- | ---: |
| Arrays testados | 24 |
| Bytes originais somados | 269.312 |
| Bytes LZ10 somados | 72.617 |
| Economia potencial bruta | 196.695 |
| Fracao bruta reduzida | ~73,0% |
| Round-trip byte a byte | PASS (24/24) |
| Economia efetiva na ROM | **0 bytes** |

Este teste usa um encoder greedy de LZ10 em Python. Nao e o melhor encoder
possivel e os arrays de overworld podem conter **varios frames**.
**Nao afirmar que o motor pode usar os arrays comprimidos diretamente**:
descompactar uma folha inteira na VRAM ocuparia mais OBJ RAM, pois o motor
World usa frames individuais. Um decoder de frame e cache propriamente
planejados precisam ser avaliados com instrumentacao de VRAM/tempo/CPU.
Nao extrapolar 73% de um grupo de 24 maiores arrays para 1.216 assets.

## Decisao tecnica

A PR #107 mostrou Route29 com **140/1.024 tiles OBJ** e ate **11/16 paletas**.
Aqui a evidencia revela que tentar fundir todos os assets inteiros seria
de baixo impacto (maximo 14.592 B). O alvo serio e compressao seletiva.

**Proximo passo real (branch nova, sem reescrever M8):**

1. Localizar a unidade geradora de `gObjectEventPic_*` no pipeline de
   World pinned e provar os contratos de frames.
2. Selecionar 1 especie/animacao grande, criar encoder offline por frame
   e decoder para buffer de um unico frame, com cache de VRAM limitado.
3. Comparar compilacoes ARM/GBA e snapshots de VRAM, heap e ciclos (nao
   apenas bytes codificados).
4. Provar fidelidade visual incluindo movimento, seguidor, OWE, shiny
   e formas; testar mapa denso, Surf e saves antes de qualquer rollout.
5. Nunca ligar `OW_GFX_COMPRESS=TRUE` globalmente sem prova dos limites,
   nem trocar etiquetas/paletas de especie apenas por igualdade em bytes.

**A ROM Master / M8 esta preservada, todos os arquivos mudados nessa PR
sao ferramentas de auditoria, testes e workflow.**
