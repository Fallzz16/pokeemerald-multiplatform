# Guia de testes manuais — Emerald Hybrid com Kanto V0.11

**Este pacote é um preview experimental para Windows, não uma versão aprovada.**
O workflow compila o executável e checa dados, mas não reproduz uma partida humana nem valida colisões e saves reais.

## Preparação

1. Baixe o artefato do workflow da branch `feature/kanto-v11-original-hidden-items` e extraia todos os arquivos em **pasta nova**; mantenha `pokeemerald.exe` e `SDL2.dll` juntos.
2. Faça uma cópia de segurança dos arquivos `.sav` e de toda a pasta de jogo atual em outro diretório. **Não experimente primeiro com seu save principal.**
3. Utilize cópia descartável de save com pelo menos quatro insígnias (pré-requisito existente para o barco) e mantenha anotados os locais de cura atuais de Hoenn.
4. Inicie o jogo pela pasta experimental, percorra o cais de Slateport, fale com o marinheiro de Kanto, confirme passagem e desembarque em Vermilion. Não altere a versão principal.
5. Para relatar qualquer problema, anote o commit do arquivo `KANTO_V11_STATUS.txt`, o mapa/cidade, a ação exata e se o erro se repete após salvar/reabrir.

## Checklist funcional — registrar OK, FALHOU ou NÃO TESTADO

- [ ] **Viagem:** embarcar no marinheiro de Slateport e chegar em Vermilion sem tela preta; recusar a viagem e ficar em Hoenn.
- [ ] **Ferry de retorno:** voltar ao último local de cura de Hoenn e confirmar que o endereço não foi sobrescrito em Kanto.
- [ ] **Centro Pokémon:** curar a equipe em Vermilion, Viridian, Pewter, Cerulean, Lavender, Celadon, Fuchsia, Cinnabar e Saffron; entrar e sair sem ficar preso.
- [ ] **Whiteout Kanto:** visitar dois Centros diferentes (ex.: Vermilion → Pewter), perder batalha em Kanto e reaparecer no segundo, não em Hoenn. Repetir após salvar e carregar; testar também uma cópia antiga sem localização Kanto gravada (fallback Vermilion).
- [ ] **Whiteout Hoenn:** perder batalha em Hoenn e verificar que reaparece no Centro Hoenn anterior, sem ser levado a Kanto.
- [ ] **Mercados:** confirmar que os oito Poké Marts oferecem estoques específicos de FireRed e que compras gastam dinheiro, adicionam itens e persistem ao salvar.
- [ ] **Viridian Forest:** percorrer as entradas norte/sul, enfrentar os cinco Bug Catchers, receber EXP/prêmio e verificar que treinadores derrotados não reiniciam após salvar/carregar.
- [ ] **Itens visíveis:** coletar ao menos 3 das 42 Poké Bolas importadas; voltar ao mesmo ponto depois de salvar/carregar e verificar que continuam desaparecidas.
- [ ] **Itens escondidos:** encontrar ao menos 3 dos 77 itens ocultos, testar o Itemfinder quando disponível e verificar persistência após reiniciar.
- [ ] **Encontros selvagens:** testar caminhar em grama e cavernas, fugir, batalhar e capturar; garantir que aparecem as espécies e níveis esperados.
- [ ] **Conexões:** atravessar Route 2 ↔ Viridian Forest; Route 2 ↔ Diglett's Cave ↔ Route 11; Route 4 ↔ Mt. Moon; Routes 5/6 e 7/8 ↔ passagens subterrâneas; Routes 5–8 ↔ Saffron; Rock Tunnel (2 pisos); Pokémon Tower (7 pisos).
- [ ] **Gráficos e colisão:** conferir passagens, portas, escadas, grama, água, bordas e animações. Reportar tiles invisíveis, sprites atravessando paredes, mapas travados ou encontros não funcionando.
- [ ] **Save/reload:** salvar fora e dentro de Centros Pokémon, em rotas e cavernas; fechar e reiniciar o executável e verificar posição, equipe, inventário e progresso.
- [ ] **Regressão Hoenn:** recuperar save de teste anterior, conferir cidades, Pokémon, caixa, batalhas, comércio e viagens normais sem alterações.
- [ ] **Rede/Android:** não homologados por este workflow; testar separadamente em dupla/Windows–Android quando existir pacote correspondente.

## Limites atuais (intencionais)

Não estão prontos: ginásios e insígnias próprias de Kanto, quests, todos os NPCs originais, música original, Pokémon Tower Ghost/Silph Scope, Rockets, Fly/PokéNav de Kanto, interiores residenciais/2F e eventos especiais. A análise de grafo aponta 83 de 84 IDs alcançáveis a partir de Vermilion; o cais antigo de teste permanece registrado, mas a viagem real entra diretamente em Vermilion. **Contagem de mapas não é medição de campanha jogável.**

## Diagnóstico de CI

- `kanto-v11-hidden-items.yml`: valida estrutura dos 84 mapas, saves sem alteração de tamanho, objetos, flags, centros, scripts, conexões e executável Windows. Resultado verde **não substitui gameplay**.
- CI geral GBA: falhas de compilação com o toolchain legado `agbcc` incluindo `_Static_assert`, `sound_mixer.h` e `battle_main.o` foram observadas no workflow; não são equivalentes ao resultado da cross-build Windows e precisam de investigação independente antes de merge.
- Em caso de falha, não use o save principal. Preserve o último pacote aprovado e relate os logs no GitHub.

## Como registrar um teste

Use: **Versão/commit**, **mapa**, **ação executada**, **resultado esperado**, **resultado encontrado**, **save novo ou reaproveitado** e **repetição após restart**. Anexe captura e log se disponível, sem publicar dados pessoais.
