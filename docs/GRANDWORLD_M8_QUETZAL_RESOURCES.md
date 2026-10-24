# M8 — Quetzal e auditoria de recursos GBA/LZ77

## Contexto e limites

- Base real: Pokémon World fixado em 15d3888b0d81322a04d3c71b0bce18948761ee44, integrado pelos scripts de tools/grandworld.
- O Pokémon Quetzal PT-BR Alpha 9 é referência de comportamento e engenharia, **não fonte copiada de código**.
- Inspeção estática da ROM fornecida pelo usuário encontrou fluxos LZ77 do tipo BIOS 0x10, mas isso **não prova** quando ocorre a descompressão nem quantos FPS são obtidos.
- Não incluir ROMs, sprites ou material derivado de terceiros no repositório.
- Preservar regiões, protagonistas e os sistemas da M8, inclusive saves. Encontros selvagens somente na grama são uma decisão do Grand World a respeitar antes de promover qualquer perfil experimental. M9 continua suspensa.
- Não promover build experimental LTO sem QA de gameplay.

## Implementado neste incremento

1. tools/grandworld/audit_lz77_resources.py: varredura somente leitura de palavras alinhadas com endereços de ROM nas janelas 0x08, 0x0A e 0x0C; valida cabeçalho e fluxos BIOS LZ77 0x10; verifica referências retrospectivas, deduplica streams e não extrai gráficos.
2. tools/grandworld/tests/test_audit_lz77_resources.py: testes sintéticos para fluxo válido/inválido, cabeçalho, ponteiros espelhados, ausência de referências e deduplicação. Não usa ROM comercial.
3. .github/workflows/grandworld-m8-performance-build.yml: gera m8-perf-lz77-comparison.json após as compilações, compara recursos de duas variantes e publica apenas métricas. ROMs não são enviadas como artefatos.

## Reproduzir com ROM própria de testes

    python3 -m unittest discover -s tools/grandworld/tests -p 'test_audit_lz77_resources.py' -v
    python3 tools/grandworld/audit_lz77_resources.py path/to/your.gba --output m8-lz77.json
    python3 tools/grandworld/audit_lz77_resources.py baseline.gba --compare optimized.gba --output m8-lz77-comparison.json

Campos: referenced_lz77_streams, referenced_stream_stored_bytes, referenced_stream_expanded_bytes, expansion_ratio, second_minus_first. Não medir FPS/ciclos por inferência destes números.

## Evidência de referência

Na ROM Quetzal enviada pelo usuário, a nova varredura de ponteiros alinhados encontrou **6.865 streams LZ77 válidos distintos**: somam **2.045.429 bytes** armazenados e **5.580.622 bytes** de tamanho declarado após descompressão, proporção **2,728:1**. São estimativas heurísticas de fluxos referenciados, não inventário exaustivo, nem ganho de desempenho. A ROM não foi publicada neste PR.

Não ativar OW_GFX_COMPRESS indiscriminadamente: compressão pode economizar espaço e simultaneamente aumentar uso de CPU, EWRAM e latência. A política existente segue inalterada.

## Próximos experimentos (não implementados)

1. Medir tempo de quadro real no mGBA em rotas densas e cenas padronizadas.
2. Associar streams LZ77 ao carregamento de mapas, sprites e paletas; detectar descompressões repetidas apenas quando houver evidência.
3. Testar cache/reuso exclusivamente em gargalos demonstrados e sob limites claros de IWRAM/EWRAM.
4. Medir pressão de OAM de seguidores/objetos e efeito das sombras (PR #70).
5. Revalidar batalhas, mapas, transições e saves com o mesmo SHA de ROM dos relatórios.

**Não incluído:** cache de runtime, alteração do motor gráfico, políticas novas de DMA, modificação de save ou de encontros, ganho comprovado de FPS, ROM de release ou homologação de gameplay deste incremento.
