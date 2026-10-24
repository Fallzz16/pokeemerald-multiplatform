# M8 — Perfis configuráveis de desempenho (Quetzal como referência)

## Decisões aprovadas em 24/10/2026

1. **1C — ambos:** fluidez no GBA físico e nos emuladores (não apenas em desktop).
2. **2C — sombras configuráveis:** dois perfis de compilação que podem ser comparados sem alteração de save. Uma alternância visual em menu durante o jogo ainda **não** foi implementada e não deve ser prometida como pronta.
3. **3C — compressão equilibrada:** manter a política gráfica comprovada pelo Pokémon World; avaliar previamente LZ77, VRAM, ROM, CPU e memória. Não ativar compressão global sem medições.
4. **4C — otimização dinâmica sem perder qualidade:** preservar culling/ordenação/cache de objetos já existentes; avaliar alocações e janelas de visibilidade por testes reais antes de alterar essas rotinas.
5. **5E — todos, por gargalos medidos:** perfilar sprites e cenas densas antes de mexer em DMA, batalhas, transições ou compressão.

## Alterações reais desta branch

Base: branch de PR #71 (auditoria LZ77) derivada de PR #70 (sombras reduzidas, guarda redundante).
Mantém todo o código M8; novas mudanças são aplicadas SOMENTE no checkout World isolado durante os workflows.

- `tools/grandworld/optimize_overworld_budget.py` tem `--shadows auto|lean|full`, com `auto` escolhido por condições de compilação:
  - `lean` utiliza as sombras estilo vanilla (durante saltos, menor pressão de OAM).
  - `full` mantém as sombras universais (mais sprites, revisão visual obrigatória).
  - `auto` escolhe `lean` se encontros visíveis e seguidores estão habilitados; fora desse contexto escolhe `full`.
  - A seleção acontece ANTES de compilar, não é uma configuração do jogador dentro do jogo.
- Na mesma otimização, `src/wild_encounter_ow.c` evita ler o estado SURF/UNDERWATER se controles estiverem bloqueados ou DexNav impedindo a atualização; preserva a validação obrigatória de encontro e a decisão de não tocar em tabelas/mapas.
- `tools/grandworld/evaluate_performance_budget.py`: checa SHA256, checksum, tamanho de ROM GBA e os números reais do linker, com reservas mínimas **8 KiB EWRAM, 2 KiB IWRAM, 1 MiB ROM**. Não aceita relatório incompleto.
- `tools/grandworld/compare_shadow_profiles.py`: compara números dos dois builds O2, prova que relatórios LZ77 e linker apontam para o mesmo SHA de ROM e calcula deltas de ROM/EWRAM/IWRAM.
- `tools/grandworld/lua/GrandWorldOamBudget.lua`: lê a OAM de hardware através do mGBA durante 180 quadros no hub e 120 quadros após movimento. Esta é evidência de uso de slots de sprites **em execução**, não de CPU/FPS.
- `tools/grandworld/parse_oam_metrics.py`: valida métricas OAM reais da execução e associa ao SHA da ROM.
- Workflows atualizados: compilação pareada O2/LTO agora exige headroom; novo workflow compila separadamente `lean` e `full` com integração M8 idêntica, valida as ROMs e publica comparação A/B. M8 de integração ganhou coleta OAM em mGBA após finalizar os 105 critérios, inicialmente **advisory** e sem aumentar os 15 critérios já homologados.
- Testes unitários adicionais usam somente fixtures sintéticas, sem distribuir recursos nem ROM comercial.

## Como reproduzir

```sh
python3 -m unittest discover -s tools/grandworld/tests -p 'test_*.py'
python3 tools/grandworld/optimize_overworld_budget.py world --shadows lean
python3 tools/grandworld/optimize_overworld_budget.py world --apply --shadows lean --report shadow-profile.json
```

Para compilar o perfil `full`, use um **novo checkout limpo e idêntico** de World e aplique a mesma sequência M8, alterando somente o parâmetro `--shadows full`. O script é deliberadamente *fail-closed* e não aceita reaplicação cega.

## Limites técnicos e de evidência

- Contar 128 entradas OAM ativas não mede ciclos consumidos, nem garante 60 FPS.
- `lean` reduz a quantidade de sombras alocáveis; o quanto economiza depende da população visível no mapa. `full` pode ficar menos estável em cenas densas: não recomendar release sem comparações.
- `OW_GFX_COMPRESS` permanece `FALSE` devido aos riscos para seguidores e encontros overworld; relatórios LZ77 não justificam o uso de descompressão recorrente.
- Não há código copiando a ROM do Quetzal para a ROM do Grand World.
- Nem a M8, nem a verificação estrita de encontros **exclusivamente na grama**, nem os 90 critérios pendentes de homologação ficam automaticamente resolvidos por este pacote. As tabelas e a lógica do spawn original não foram editadas. É necessário QA específico antes de afirmar a regra grass-only para todos os casos.
- Não modificar SaveBlocks, campanhas regionais, Pokémon da equipe, escolha de protagonistas, gameplay multiplayer ou M9.
- Não apresentar resultados de build como testes visuais de jogabilidade ou como uma ROM de release pronta.

## Critérios de promoção

1. Python preflight PASS, ambas compilações O2 PASS, validação `make validate` PASS, cabeçalho/memória PASS, relatórios do mesmo SHA.
2. Integração mGBA obrigatória de 51 suítes sem regressões e evidência de ROM correta.
3. Inspeção visual e gameplay do perfil completo com cidades lotadas, seguidores e encontros (preferencialmente GBA real além do mGBA).
4. Medição reproduzível de **tempo por quadro** antes de afirmar ganho de FPS.
5. Atualização dos critérios M8 apenas com evidência de gameplay e continuidade correta de save.

**Rollback:** branch e PR de experimento independentes; a base PR #71 e sua ancestral PR #70 continuam intactas, assim como main.
