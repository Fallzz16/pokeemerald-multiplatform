# Pokémon Grand World pós-M8 — encontros na grama (experimental)

Data: 24/10/2026.

Base da branch:
- Grand World: perf/grandworld-m8-configurable-profiles-20261024, commit 869314ca6c2a1e1828d8d12231a426ac07c1e5eb.
- Pokémon World isolado: evilchinesefood/PKMN-World, commit 15d3888b0d81322a04d3c71b0bce18948761ee44.
- Os PRs #70, #71 e #72 não foram mesclados.

## Decisões preservadas

Respostas: 1E 2D 3D 4E 5E 6E 7E 8E 9A 10E 11A 12E 13E 14E 15E 20E.
As outras perguntas ficam sob decisão técnica. Campanhas independentes (11A),
transporte por pontos estratégicos (2D), conteúdo exclusivo inicial focado
em eventos principais regionais (9A). M9 multiplayer continua adiado.

## Código novo

tools/grandworld/apply_grass_only.py edita apenas o checkout Word isolado,
depois de optimize_overworld_budget.py, antes da compilação.

1. WE_OW_ENCOUNTERS fica FALSE. WE_VANILLA_RANDOM permanece TRUE. Não apaga
   Pokémon seguidores nem objetos estáticos colocados por roteiro.
2. Acrescenta GW_GRASS_ONLY_WILD = TRUE sem tocar em SaveBlock.
3. StandardWildEncounter requer grama alta/longa/pokégrass ou grama de cinzas.
4. SweetScentWildEncounter requer os mesmos tipos de grama.
5. RockSmashWildEncounter retorna FALSE sem iniciar batalha selvagem.
6. DoesCurrentMapHaveFishingMons retorna FALSE; FishingWildEncounter dispõe
   de guarda defensiva para chamadas diretas.
7. StandardWildEncounter_Debug não ignora a regra.

Mantém tabelas existentes, roamer, níveis e repelente para encontros de grama.
O patch exige âncoras exatas e rejeita alterações inesperadas antes de escrever.
Faz backups .gw-grass-original somente no checkout de CI. Não reaplicar
sobre o mesmo checkout; perfis lean e full exigem árvores limpas separadas.

## Pendências obrigatórias antes de release

- Pokémon estáticos e eventos de história não são alterados: requisito literal
  de nenhum encontro selvagem fora da grama ainda requer auditoria por script.
- Retirar pesca, água e Rock Smash pode deixar espécies inacessíveis.
  É obrigatório examinar e realocar disponibilidades em grama por região,
  sem renumerar espécies nem substituir o save.
- Testar pesca sem travamento e sem batalha, rochas, Sweet Scent, Safari,
  Battle Pike/Pyramid, DexNav, eventos de lendários, minigames e tutoriais.
- Conferir interações com seis heróis, seguidores, mudança de região,
  salvar, desligar, carregar, campanha e ginásios.
- Não reportar FPS, ganho de desempenho ou homologação sem medição.

## Reprodução e evidências

Preflight sem modificar a árvore:

    python3 -m unittest discover -s tools/grandworld/tests -p 'test_*.py'
    python3 tools/grandworld/apply_grass_only.py world

Em World limpo e já integrado às adaptações M8:

    python3 tools/grandworld/optimize_overworld_budget.py world --apply --shadows lean
    python3 tools/grandworld/apply_grass_only.py world --apply --report postm8-grass-only.json
    make -C world modern -j2
    make -C world validate

Os workflows de compilação receberam o adaptador após otimização. A matriz
lean/full produz ROMs experimentais distintas, hash SHA256, manifesto e
orçamento de memória; a integração mGBA preserva as 51 suítes obrigatórias.

P0: compilar e validar as 51 suítes, os perfis, controles da ROM e memória,
regressão save/Continue, passos na grama e fora, pesca e Rock Smash.
P1: reparar disponibilidade de espécies, mapear exceções scriptadas,
melhorar conteúdo das três campanhas e viagens.
P2: polimento gráfico, novos eventos secundários e animações.

CI verde de build NÃO significa gameplay homologado. Release ainda bloqueada.
Rollback seguro: retornar ao commit-base
869314ca6c2a1e1828d8d12231a426ac07c1e5eb;
não mesclar automaticamente o PR experimental.
