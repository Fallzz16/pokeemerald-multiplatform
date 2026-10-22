# Pokémon Emerald Hybrid — situação, backlog e prioridades

Atualizado em 22/10/2026. Linha experimental V0.19 em `feature/kanto-v19-route3-trainers`, derivada de V0.18 PR #49. PRs #51/#53/#54/#55 são linhas paralelas divergentes; não mesclar diretamente.

## Estado implementado — sem extrapolar jogabilidade

| Área | Estado real | Pendências |
|---|---|---|
| Exteriores FireRed | 38 mapas com tiles, metatiles, layouts e colisão convertidos por gerador | comportamentos especiais, ciclos dia/noite, animações e inspeção visual |
| Interiores | 17 Centros/Marts, 4 portões Saffron, 9 áreas Viridian/MtMoon/Diglett, 15 entradas/pisos Underground/RockTower, 1 cais legado = 84 mapas grupo Kanto | interiores de ginásios, residências, S.S. Anne, dungeons restantes |
| Viagens | Slateport → Vermilion, retorno ao último heal registrado em Hoenn | QA de embarque/recusa e saves legados |
| Serviços | Cura em nove Centros e mercados com estoques originais FireRed | whiteout Kanto integrado no motor V0.10; validar realmente depois de derrota e save |
| Pokémon selvagens | dados FireRed nas áreas portadas onde aplicáveis | QA de grama/caverna/água, níveis, batalhas, captura |
| Itens | 42 Poké Bolas visíveis + 77 itens escondidos originais, flags salvas exclusivas | QA de coleta/Itemfinder/persistência |
| Treinadores | 22 NPCs com batalhas geradas: 8 líderes e 14 comuns (inclui 4 V0.19 Route 3) | QA real, demais treinadores, Rocket, ginásios e Liga |
| Conectividade | 83/84 mapas alcançáveis pelo grafo desde Vermilion | colisão/transições reais, mapa Harbor legado fora do grafo |
| Compilação | workflow específico Kanto Windows da V0.11 | CI GBA geral tem falha em toolchain legado; QA humano Windows/Android/rede faltante |

## Ordem de execução sugerida para as próximas sessões

1. **P0 — QA jogável**: testar executável Windows em cópias de saves. Reproduzir barco, cura/whiteout nos nove Centros, salvar/carregar em Kanto, compra, item visível/oculto, cinco treinadores, encontros e portas. Registrar correções de quaisquer travamentos/colisões encontrados.
2. **P0 — integridade de engine**: medir comportamentos desconhecidos em atributos de metatiles FireRed convertidos; corrigir tiles críticos sem quebrar Hoenn. Corrigir CI GBA genérico ou documentar claramente sua incompatibilidade preexistente com toolchain (não ocultar falhas).
3. **P1 — arquitetura de treinadores**: `MAX_TRAINERS_COUNT=864` é fixo no save; IDs 864–876 têm tradução para flags independentes, sem expandir SaveBlock. O pool de 189 flags Kanto auditado fica esgotado na V0.19: ampliar apenas com mapeamento e teste de colisão de flags persistentes. Proibir colisões com flags de ginásio/sistema de Hoenn.
4. **P1 — jornada**: portar NPCs, falas adaptadas, equipes reais, ginásios, insígnias regionais, Rocket, puzzles Ghost/Silph Scope, MtMoon fossils, S.S. Anne e eventos específicos.
5. **P1 — mapa**: terminar cavernas, portas, casas, portos e edifícios ausentes com fonte e gráficos originais. Foco nas conexões que liberam progressão, não apenas contagem de mapas.
6. **P2 — sistemas regionais**: Fly/PokéNav mapa Kanto, cidades no mapa, música, animações de água/portas, itens-chave e salvamentos/respawn/mobilidade completos.
7. **P2 — compatibilidade**: regressões completas de Hoenn, Cable Club, LANP/EHL8, multiplayer entre regiões, Windows + Android. Distinguir builds nativas dos builds GBA.
8. **P3 — integração final**: QA de progressão ponta a ponta, saves antigos, carga de jogo, FPS, traduções e guia de uso; só então considerar merge/release.

## Critérios que NÃO autorizam concluir tarefa
Compilar não comprova que o personagem pode andar corretamente; flag alocada não comprova persistência após reinício; número de mapas não comprova horas de aventura; grafo ligado não comprova que scripts e triggers funcionam; PR draft não é release estável.

## Em todas as próximas respostas
Apresentar **o que foi feito, o que foi testado, o que falta e o próximo foco**, com links aos commits/PRs/artefatos verificados. Executar tanto trabalho seguro quanto possível sem estabelecer horas arbitrárias e sem prometer execução assíncrona. Respostas 250/250 já decididas no documento de especificação.
