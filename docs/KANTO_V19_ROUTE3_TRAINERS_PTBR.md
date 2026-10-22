# Kanto V0.19 — treinadores de Route 3 e flags de vitória

**Branch isolada:** `feature/kanto-v19-route3-trainers` sobre `feature/kanto-v18-moon-route3-trainers`, commit de origem `a353c7179b1ab73bd8ce32726eadade95679c615`.
**FireRed pinado:** `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`.
**Estado:** trabalho experimental em draft; compilação e gameplay devem ser avaliados individualmente.

## Implementação efetiva
- Novo gerador `tools/kanto/v19_trainers.py` materializa as Lasses **Robin, Sally, Janice** e o Youngster **Calvin** na Route 3.
- Os quatro atores reproduzem posição, classe, movimento, direção/range de visão e equipes do FireRed selecionado. A batalha é roteirizada em Emerald via `trainerbattle_single`; as falas continuam provisórias.
- IDs **873–876**, acrescentados sem reordenar 855–872. `TRAINERS_COUNT` passa a **877**, e `MAX_TRAINERS_COUNT=864` continua intocado para preservar o tamanho do save.
- Quatro flags de vitória específicas, mapeadas em `src/battle_setup.c` (mesmo tratamento em consultas, vitórias e limpeza de flags). Não reutilizar flags anteriores.
- Esperam-se **114 mapas em dois grupos, 22 treinadores de batalha de Kanto (8 líderes e 14 comuns) e 160 itens coletáveis** no relatório de geração.
- Pool atual de **189 flags Kanto** após gerar a V0.19: 160 itens, 8 primeiras recompensas, 12 flags dos últimos quatro líderes, 5 vitórias V0.18 e 4 V0.19. Todas devem permanecer exclusivas.

## Verificações e limitações
O workflow `.github/workflows/kanto-v18-moon-route3-trainers.yml` agora escuta a branch V0.19, importa FireRed pinado, executa `tests/test_kanto_v19_route3.py` e prossegue com as verificações estruturais e o cross-build Windows já existentes. O novo teste compara coordenadas, comportamento, equipes, IDs, flags e scripts. Nenhum dos testes lê ou modifica saves pessoais.

**Não confundir:** ter código versionado, arquivos gerados, build verde e funcionamento confirmado em jogo são etapas distintas. Até confirmar os workflows no SHA correto, não declarar build aprovado. Mesmo com build aprovado, continua faltando teste real de visão dos treinadores, derrota/vitória, reload de save e câmera.

## Bloqueio de expansão
O conjunto de flags UNUSED que vinha sendo auditado está esgotado após a V0.19. **Não portar outro treinador sem primeiro projetar e testar outro espaço comprovadamente livre e persistente**, compatível com Hoenn, saves antigos e os sistemas Hybrid. Não aumentar `MAX_TRAINERS_COUNT` nem mexer em offsets de SaveBlock.

## QA manual obrigatório
Em uma instalação Windows experimental e cópias descartáveis de saves:
1. Entrar pela travessia Hoenn → Kanto, caminhar em Route 3 e ativar os quatro encontros por visão.
2. Conferir equipes, níveis, derrota, diálogos, marcar vitória, salvar, fechar e reabrir. Cada treinador deve continuar derrotado depois de recarregar.
3. Testar retorno a Hoenn, cura/whiteout, lojas, itens, interiores, cavernas, lideranças e Pokémon selvagens.
4. Depois verificar regressões offline, Cable Club e LAN/EHL8 com dois jogos gráficos reais, sem misturar versões ou sobrescrever .sav.

**Rollback:** preservar a V0.18 em `a353c7179b1ab73bd8ce32726eadade95679c615`; não fazer merge na main até QA real. CI genérico GBA deve ser investigado separadamente de build Windows.
