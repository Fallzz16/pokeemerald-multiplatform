# Pokémon Emerald Hybrid — situação, backlog e prioridades

Atualizado em 23/10/2026. Linha mais recente em draft V0.23 `feature/kanto-v23-mtmoon-fossil-choice`, a partir da PR #59 V0.22. Sem merge na main; conteúdos gerados ainda precisam de gameplay real.

## Estado implementado — sem extrapolar jogabilidade

| Área | Estado real | Pendências |
|---|---|---|
| Exteriores FireRed | 38 mapas com tiles, metatiles, layouts e colisão convertidos por gerador | comportamentos especiais, ciclos dia/noite, animações e inspeção visual |
| Interiores | 17 Centros/Marts, 4 portões Saffron, 9 áreas Viridian/MtMoon/Diglett, 15 entradas/pisos Underground/RockTower, 1 cais legado = 84 mapas grupo Kanto | interiores de ginásios, residências, S.S. Anne, dungeons restantes |
| Viagens | Slateport → Vermilion, retorno ao último heal registrado em Hoenn | QA de embarque/recusa e saves legados |
| Serviços | Cura em nove Centros e mercados com estoques originais FireRed | whiteout Kanto integrado no motor V0.10; validar realmente depois de derrota e save |
| Pokémon selvagens | dados FireRed nas áreas portadas onde aplicáveis | QA de grama/caverna/água, níveis, batalhas, captura |
| Itens | 42 Poké Bolas visíveis + 77 itens escondidos originais, flags salvas exclusivas | QA de coleta/Itemfinder/persistência |
| Treinadores | 50 NPCs de batalha previstos após geração V0.23 (8 líderes e 42 comuns), incluindo Miguel MtMoon_B2F | QA humano; roteiro Rocket, Miguel e fósseis, retratos/sprites, puzzles da Liga |
| Conectividade | 83/84 mapas alcançáveis pelo grafo desde Vermilion | colisão/transições reais, mapa Harbor legado fora do grafo |
| Compilação | workflow específico Kanto Windows da V0.11 | CI GBA geral tem falha em toolchain legado; QA humano Windows/Android/rede faltante |

## Ordem de execução sugerida para as próximas sessões

1. **P0 — QA jogável**: testar executável Windows em cópias de saves. Reproduzir barco, cura/whiteout nos nove Centros, salvar/carregar em Kanto, compra, item visível/oculto, cinco treinadores, encontros e portas. Registrar correções de quaisquer travamentos/colisões encontrados.
2. **P0 — integridade de engine**: medir comportamentos desconhecidos em atributos de metatiles FireRed convertidos; corrigir tiles críticos sem quebrar Hoenn. Corrigir CI GBA genérico ou documentar claramente sua incompatibilidade preexistente com toolchain (não ocultar falhas).
3. **P1 — arquitetura de treinadores**: MAX_TRAINERS_COUNT=864/SaveBlock intactos. V0.23 reserva 0x90C Miguel derrotado, 0x90D fósseis concluídos, 0x90E Dome e 0x90F Helix. Total 221 flags Kanto exclusivas; restam 16 bits conservadores 0x910–0x91F antes do reset diário 0x920. Ampliar com auditoria de colisões e saves.
4. **P1 — jornada**: portar NPCs, falas adaptadas, equipes reais, ginásios, insígnias regionais, Rocket, puzzles Ghost/Silph Scope, MtMoon fossils, S.S. Anne e eventos específicos.
5. **P1 — mapa**: terminar cavernas, portas, casas, portos e edifícios ausentes com fonte e gráficos originais. Foco nas conexões que liberam progressão, não apenas contagem de mapas.
6. **P2 — sistemas regionais**: Fly/PokéNav mapa Kanto, cidades no mapa, música, animações de água/portas, itens-chave e salvamentos/respawn/mobilidade completos.
7. **P2 — compatibilidade**: regressões completas de Hoenn, Cable Club, LANP/EHL8, multiplayer entre regiões, Windows + Android. Distinguir builds nativas dos builds GBA.
8. **P3 — integração final**: QA de progressão ponta a ponta, saves antigos, carga de jogo, FPS, traduções e guia de uso; só então considerar merge/release.

## Critérios que NÃO autorizam concluir tarefa
Compilar não comprova que o personagem pode andar corretamente; flag alocada não comprova persistência após reinício; número de mapas não comprova horas de aventura; grafo ligado não comprova que scripts e triggers funcionam; PR draft não é release estável.

## Em todas as próximas respostas
Apresentar **o que foi feito, o que foi testado, o que falta e o próximo foco**, com links aos commits/PRs/artefatos verificados. Executar tanto trabalho seguro quanto possível sem estabelecer horas arbitrárias e sem prometer execução assíncrona. Respostas 250/250 já decididas no documento de especificação.

## V0.24 — auditoria estática validada e pendências priorizadas

Ferramenta `tools/kanto/tile_audit.py` e workflow de 114 mapas: [CI 39918532192 (SUCCESS)](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/39918532192). Relatório anexo: 25 mapas com alertas, 4 eventos possivelmente inacessíveis, 21 mapas com caminhos de warps divididos, zero eventos fora das dimensões. Lista de mapas/limites em `docs/KANTO_V24_TILE_ACCESSIBILITY_PTBR.md`. **Não** confundir heurística estática com gameplay ou falhas confirmadas.

P0: reproduzir no emulador o NPC Harbor, warps de Lorelei/Bruno/Agatha e Mt. Moon, Saffron Gym, Seafoam e Victory Road; validar caminhos reais e flags após reload com saves descartáveis. P0 paralelo: finalizar ROM GBA ARM moderno e corrigir toolchain agbcc separadamente na PR #61, sem regressão Windows. Não remover tiles, alterar scripts ou tocar em saves para silenciar avisos.

## V0.25 — build GBA moderno verde, QA mGBA em expansão

- `MODERN=1 COMPARE=0` produziu ROM GBA válida de 32 MiB. [CI 40054551944](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40054551944) validou cabeçalho, linker, áudio MP2K e mGBA até o caminhão de Littleroot após NEW GAME. Isto **não** equivale a QA completa da ROM nem à prova de saves.
- P0: sair do caminhão via triggers (3,1..3) → warp (4,1..3), passear, pegar item, testar batalha e save/reload com save descartável. Revisão 45 mil quadros 818587c8 implementada; não alegar warp antes de inspecionar screenshots.
- P0: revisar limites EWRAM ~95,26%, IWRAM ~92,83%; segurança do cartucho e SRAM ao executar mais regiões.
- P1: `agbcc` antigo ainda falha nas declarações anônimas de áudio; manter não-bloqueante, com log e sem simular sucesso. Priorizar ROM moderna estável antes de recuperar a comparação legado.
- P1/P2: Windows entre 2 PCs, Android, história Kanto, sprites e QA longa. Sem merge da PR #61 antes da validação visual.
