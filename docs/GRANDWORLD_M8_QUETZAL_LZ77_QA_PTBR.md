# M8 — auditoria de recursos GBA inspirada no Pokémon Quetzal

**Data:** 24/10/2026. **Status:** experimento de diagnóstico, sem mudança no jogo ou nos saves. **Base:** PR #70 (commit inicial `f5001bc2aacb9c2c7ea582ab8669a245df48625b`). Este incremento usa uma branch separada e não altera a release.

## Evidência verificada

A ROM de Quetzal fornecida pelo usuário foi lida localmente, sem distribuição de seus bytes. Arquivo de 32 MiB, cabeçalho GBA válido, game code `BPEE`, SHA-256 `920b43b15f86716fd42cb1f362ee158019cefcda811d47c213d2366cdf019265`.

Uma varredura **heurística por ponteiros de ROM alinhados a 4 bytes** encontrou **6.865 fluxos LZ77 tipo 0x10 plausíveis e referenciados** por 7.806 campos de ponteiro. Tamanhos declarados: **2.045.429 bytes armazenados** para **5.580.622 bytes expandidos** (razão **2,728:1**). Esta contagem não representa todos os assets; pode incluir falsos positivos e omitir dados sem ponteiros ou em outros formatos. Contagens de outros métodos não são diretamente comparáveis.

**Não houve benchmark de FPS/ciclos**, inspeção de execução em hardware nem comprovação de que o autor do Quetzal criou uma rotina inédita. A compressão reduz armazenamento, mas pode aumentar custo de CPU/VRAM.

A base World fixada para o Grand World já implementa `LZ77UnCompWram`, `LZ77UnCompVram` e `FastLZ77UnCompWram`. A configuração `OW_GFX_COMPRESS = FALSE` é proposital e o código alerta para limites de VRAM quando Pokémon aparecem no mapa. **Não alterar essa política indiscriminadamente.**

## Técnica entregue para a M8

- Novo `tools/grandworld/audit_lz77_resources.py`: valida cabeçalho e checksum de cartucho GBA; varre ponteiros das três janelas de ROM; verifica comprimento/back-references dos fluxos sem descomprimir recursos; produz apenas métricas, SHA-256 e avisos JSON, nunca material de sprites, mapas ou ROM.
- Novo `tools/grandworld/tests/test_audit_lz77_resources.py`: cinco testes com bytes sintéticos (headers, espelhos, backrefs, ROMs inválidas, comparação e imutabilidade dos arquivos).
- O workflow de integração M8 passa a auditar a ROM montada, armazenando apenas relatório JSON nos diagnósticos — **não disponibiliza .gba**.
- O PR #70 já possui experimento de economia OAM por política de sombras e eliminação de checagem redundante de flag, ainda sem medida de FPS. Esta entrega **não afirma** que a auditoria sozinha melhora o FPS.

### Execução local

```bash
python3 tools/grandworld/audit_lz77_resources.py caminho/rom.gba --output relatorio-lz77.json
python3 tools/grandworld/audit_lz77_resources.py caminho/versao-a.gba --compare caminho/versao-b.gba --output comparacao.json
python3 -m unittest discover -s tools/grandworld/tests -p 'test_audit_lz77_resources.py' -v
```

Os relatórios de ROMs diferentes não provam desempenho; somente comparar **builds equivalentes do Grand World**, acompanhado de QA mGBA e métricas runtime, permite avaliar uma otimização.

## Próximas melhorias possíveis (não implementadas)

1. Instrumentar tempo de CPU por quadro, tempo de DMA/VBlank e slots OAM em mapas lotados; produzir baseline comparável por hash SHA.
2. Medir custo e frequência de descompressão/carregamento gráfico em mudanças de mapa; testar cache/preload seletivos **antes** de adotar.
3. Testar perfis LTO `-O2` com mesmos defines, saves e cenários de gameplay.
4. Preservar três regiões, seis protagonistas, equipe compartilhada e saves, sem habilitar M9.

**Divergência herdada:** o World fixado atualmente tem `WE_OW_ENCOUNTERS = TRUE` (selvagens visíveis no cenário), embora a decisão do usuário para Grand World seja **encontros selvagens exclusivamente na grama**. O presente PR não altera isso; corrigir em incremento próprio com testes de gameplay. Nunca tratar o comportamento herdado como uma nova decisão do usuário.

## Verificações e rollback

**Executado localmente:** auditoria da ROM enviada e cinco testes unitários de exemplo, aprovados. **Ainda não executado aqui:** build Grand World, mGBA com a ROM resultante, FPS em execução ou comparação CPU. Testes de CI só contam após conferir SHA e logs de runs novos.

**Rollback:** reverter arquivos da auditoria/documentação e pequena adição do workflow desta branch, sem tocar no PR #70, main, arquivos .sav ou sistema de encontros.
