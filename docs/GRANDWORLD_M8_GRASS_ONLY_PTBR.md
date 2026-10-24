# M8 — Encontros selvagens clássicos na grama

## Decisão aplicada

Restaurar o comportamento de encontros aleatórios na **grama** e retirar os Pokémon selvagens gerados e visíveis no mapa, conforme a decisão recorrente do jogador. Esta etapa é uma alteração real da ROM compilada, não somente documentação.

**Escopo exato da regra:**

- Pokémon selvagens de **terra** surgem aleatoriamente quando o jogador pisa em grama alta, longa ou gramado com cinzas de Hoenn.
- Terreno comum e pisos de cavernas **deixam de ativar encontros terrestres aleatórios**. É uma consequência importante da interpretação literal "somente na grama"; pode ser revertida em uma iteração posterior se desejado.
- Mantém encontros de **água ao surfar**, pesca, Rock Smash, Pokémon fixos e eventos especiais/roteirizados, por não serem encontros terrestres aleatórios. Na Battle Pike/Pyramid, a lógica própria de desafio permanece.
- Pokémon acompanhantes, sprites de NPCs, Pokémon visíveis de história, viagens livres, regiões, equipe carregada, seis heróis, tabelas de espécies/níveis/taxas e salvamentos não são alterados.
- A configuração de origem da ROM era `WE_VANILLA_RANDOM TRUE` e `WE_OW_ENCOUNTERS TRUE`. O projeto experimenta agora `TRUE` e `FALSE`, respectivamente.

## Implementação

`tools/grandworld/enable_classic_grass_encounters.py` roda **após** `optimize_overworld_budget.py` no checkout de teste do Pokémon World:

1. Mantém encontros aleatórios padrão habilitados.
2. Desabilita a geração automática de Pokémon selvagens visíveis no overworld.
3. Acrescenta entrada antecipada em `UpdateOverworldWildEncounter` que, no perfil desligado, libera OWEs geradas restantes e impede escanear o mapa no mesmo frame. Mantém a limpeza normal do sistema quando desabilitado.
4. Restringe o gatilho terrestre normal e o de Sweet Scent à grama, com as APIs nativas `MetatileBehavior_IsTallGrass/IsLongGrass/IsAshGrass`.
5. Aplica edição fail-closed e escreve relatório JSON reproduzível.

Nenhuma estatística de FPS ou de CPU foi inferida dessa alteração. O resultado real precisa ser aferido em cenas equivalentes com save e emulador.

### Reproduzir, sem editar a origem nem sobrescrever o build anterior

```sh
python3 -m unittest discover -s tools/grandworld/tests -p 'test_enable_classic_grass_encounters.py' -v
python3 tools/grandworld/enable_classic_grass_encounters.py /tmp/world-clean
python3 tools/grandworld/enable_classic_grass_encounters.py /tmp/world-after-m8 --apply --report grass-encounters.json
```

A última linha só aceita o World na versão/padrão esperado **depois da aplicação de M8**. Não é permitida reaplicação sobre código já modificado. `--apply` realiza as três alterações após verificar todos os anchors.

## QA e não regressão

- Testes Python sintéticos: versão original, isolamento, alteração dos dois gatilhos, preservação de pesca/água, idempotência fail-closed, configuração clássica exigida e source drift.
- Matriz GitHub compila e publica variantes `lean` e `full`; `grass-encounters.json` acompanha diagnósticos e o manifesto/arquivo `.gba` deve ser da mesma execução/commit.
- Workflow de integração M8 continua compilando o World com os personagens/regiões, exige as 51 suítes de gameplay com o **mesmo SHA de ROM** e verifica salvamento/viagens quando suportado; emuladores e GBA real podem apresentar diferenças.
- Se alguma suíte anterior dependia de Pokémon **visíveis gerados** na rota, deve ser marcada como incompatível com a nova regra e substituída por teste equivalente — jamais omitir uma falha para inflar a homologação. O objetivo é ter resultados verdes com a regra de produto correta.

## Limitações

**Ainda não significa 105/105 critérios M8 concluídos.** As campanhas e pós-jogo de todas as regiões permanecem em integração, e a M9 multiplayer está suspensa. Não modifica as taxas originais de encontro de cada mapa, mas pisos de caverna sem grama deixarão de receber encontros aleatórios de terra. A coleta de itens/quests e Pokémon fixos continuam respeitando os scripts do World de base.

**Rollback**: descartar PR/branch experimental, não mexer na PR #72 já testada, nem nos arquivos reais do usuário.
