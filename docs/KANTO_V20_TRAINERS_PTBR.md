# Kanto V0.20 — 22 novos treinadores de rotas, Mt. Moon e Cerulean Gym

**Origem:** PR #56 V0.19 (`564ba7a25bafb650c67e587b688af5f86f793165`). **Branch:** `feature/kanto-v20-route-moon-trainer-expansion`. **FireRed:** commit fixo `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`. Não fazer merge em main antes de QA gráfico real.

## Implementado na geração

22 novos treinadores originais (IDs **877–898**):
- Route 3: Youngster Ben.
- Route 4: Lass Crissy.
- Mt. Moon 1F: Lass Iris, Lass Miriam, Youngster Josh, Hiker Marcos.
- Route 24: Camper Ethan, Lass Reli, Youngster Timmy, Lass Ali, Bug Catcher Cale, Camper Shane.
- Route 25: Hiker Franklin, Youngster Joey, Hiker Wayne, Youngster Dan, Picnicker Kelsey, Hiker Nob, Camper Flint, Youngster Chad, Lass Haley.
- Cerulean Gym: Picnicker Diana.

O importador `tools/kanto/v20_trainers.py` retira coordenadas, visão, movimentação, sprites, classe, retrato, música de encontro/gênero, espécies, níveis e equipes da fonte FireRed. Recusa party desconhecida, nome duplicado, evento em célula ocupada, símbolos ausentes e falha de flags. Scripts `trainerbattle_single` recebem falas provisórias. Não significa eventos da campanha terminados.

Totais **esperados após materialização:** **114 mapas**, **160 pickups**, **44 treinadores (8 líderes + 36 comuns)** e **211 flags exclusivas para conteúdo de Kanto**.

## Contrato de saves

As 189 flags da V0.19 permanecem intocadas. As 22 novas vitórias usam `FLAG_UNUSED_0x8F0` até `FLAG_UNUSED_0x905`, traduzidas explicitamente em `src/battle_setup.c` gerado. Correspondem à faixa SYSTEM_FLAGS e estão antes das flags diárias que iniciam em `0x920`. São persistentes no SaveBlock1, não limpas pela rotina ClearDailyFlags. O importador verifica o formato e os valores exatos da faixa antes de usá-la.

`MAX_TRAINERS_COUNT=864` continua idêntico no campo original de save. Somente `TRAINERS_COUNT=899` controla o array de dados de treinadores. Não aumentar SaveBlock ou renumerar mapa, treinador/flag antigo. Restam **26 bits não utilizados** no intervalo adicional auditado 0x906–0x91F; cada uso futuro exige nova conferência.

## Testes

`tests/test_kanto_v20_extended_trainers.py` compara eventos e parties byte a byte com a revisão FireRed pinada; auditam classe, sprite, visão, coordenada, estado dos IDs, faixa persistente e exclusividade das flags. `tests/test_kanto_v19_route3.py` foi mantido compatível com a nova geração. Workflow específico: `.github/workflows/kanto-v20-common-trainers.yml`, com importador, testes anteriores, grafo e cross-build Windows.

**CI e gameplay não são sinônimos.** Verificar o resultado no commit exato do GitHub Actions. Testar 22 encontros em Windows real, vitória e derrota, salvar/fechar/reabrir, cure/whiteout, Hoenn↔Kanto, gráficos e regressões antes de declarar jogável.

## Pendências

Ainda faltam scripts Rocket, Silph, fósseis e S.S. Anne; maioria das áreas interiores, puzzles dos ginásios, Elite Four/Champion/Hall of Fame, música e arte, PokéNav/Fly regional, Android, rede e QA de saves reais. CI GBA genérico é pipeline separado. A expansão segue DRAFT.

**Rollback:** V0.19 PR #56 HEAD acima; instalar previews em pasta nova e usar somente cópias de saves.
