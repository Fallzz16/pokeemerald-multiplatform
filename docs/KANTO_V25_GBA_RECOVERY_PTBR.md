# Kanto V0.25 — ROM GBA moderna e testes reais no mGBA

**Estado:** recuperação da compilação ARM moderna comprovada e introdução de novo jogo executada em mGBA. **Não é release nem validação completa de gameplay.** Branch `feature/kanto-v25-gba-recovery-modern-legacy`, PR draft #61 sobre PR #62 (V0.24). Revisão fixa de FireRed: `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`.

## Erros reais corrigidos

1. `include/gba/macro.h`: `#if defined MODERN` entrava no caminho C11 com `MODERN=0`. Agora exige valor verdadeiro de `MODERN`.
2. `Makefile`: GBA compilava fontes exclusivas do Windows: BIOS simulada, backup POSIX, TCP/LAN nativo, stubs e mixer de float. A seleção é separada por plataforma, e `Makefile_pc` permanece funcional.
3. `audio_rules.mk`: defaults explícitos das transformações GAS evitam executar `.s` como comando.
4. `src/music_player.c`: mantém o interpretador MP2K compartilhado mas retira do GBA símbolos implementados em assembly; evita duplicação de símbolos do linker.
5. `include/gba/m4a_internal.h`: restaurado buffer DirectSound de 8 bits e dimensões apropriadas à ROM; buffer estéreo float fica somente no port nativo.
6. `src/quest_log.c`: handles agora são zero-inicializados em BSS, com inicialização em Open e fechamento seguro quando a UI ainda não abriu. Evita `.data` descartada no linker do cartucho, sem alterar SaveBlock.
7. `.github/workflows/build.yml`: jobs GBA moderno (requerido) e compilador legado (diagnóstico não bloqueante) separados. Ambos materializam antes os 114 mapas e treinadores Kanto da mesma revisão FireRed. Hash igual ao Emerald original **não** é critério válido para a ROM modificada.

## Compilação e memória comprovadas

- [Actions #40051271009](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40051271009): primeira ROM GBA moderna compilada.
- [Actions #40054551944](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40054551944): GBA moderno e mGBA 30 mil quadros aprovados no commit `6f257ce5`. Artefatos `KANTO_V25_GBA_MODERN` e `KANTO_V25_MGBA_HEADLESS_ADVISORY`.
- [Actions #40054910573](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40054910573): no commit `818587c8` o build ARM moderno passou. A tentativa de 45 mil quadros da saída do caminhão ainda precisava do resultado do runner mGBA durante a redação deste documento.
- `pokeemerald_modern.gba`: 33.554.432 bytes (32 MiB, cartucho preenchido; não é tamanho efetivo de código). O linker mostrou ROM ~18.651.800 bytes, EWRAM 249.712/262.144 bytes (95,26%) e IWRAM 30.420/32.768 bytes (92,83%). **Pouca folga de RAM**; nunca adicionar buffers sem medir.
- `tools/kanto/gba_rom_audit.py` valida braço de entrada, cabeçalho, marca, game code `BPEE`, maker, logo e complement checksum, SHA256 e capacidade. `gba_memory_audit.py` registra maiores símbolos BSS. Nenhum desses resultados demonstra integridade de saves ou gameplay.

## Capturas do emulador — somente o que foi observado

- [mGBA 9.600 quadros / Actions #40053915377](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40053915377): copyright, animação Game Freak, intro de Pokémon Emerald, tela de título, menu **NEW GAME/OPTION** e Professor Birch.
- [mGBA 30.000 quadros / Actions #40054551944](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40054551944): sequência de apresentação de Birch, início do jogo, **personagem dentro do caminhão de mudanças em Littleroot**, interação com caixas. As capturas `.ppm` integram o artefato do workflow e foram verificadas visualmente.
- Ferramenta `tools/kanto/gba_headless_smoke.c` é o próprio executável headless de mGBA, com teclas determinísticas, frames e relatórios. Usa arquivos temporários de runner e **não carrega/restaura saves de usuários**.
- A revisão de 45.000 quadros experimenta o deslocamento lateral e inferior e registra capturas para posterior inspeção. Os eventos de `data/maps/InsideOfTruck/map.json` mostram warp dinâmico em (4,1), (4,2) e (4,3), após triggers em (3,1..3). **Não afirmar que saiu do caminhão até a captura provar**.

## Agbcc legado: permanece bloqueado

O compilador antigo ainda rejeita unions anônimas em `include/sound_mixer.h` e estrutura incompleta ou extensões de `include/music_player.h`; ver `KANTO_V25_GBA_AGBCC_LOG`. Isso é um problema **separado** do build `MODERN=1` já funcional. Não remover avisos indiscriminadamente nem fingir `Compare` binário contra a ROM não modificada.

## Reproduzir no Linux

Com ARM GCC, libnewlib, binutils, Python/Pillow e `firered-source` na revisão fixa:
```bash
python -m unittest discover -s tests -p 'test_gba_*.py' -v
python tools/kanto/import_exteriors.py --firered firered-source --emerald . --report kanto-gba-materialization.json
make -j2 MODERN=1 COMPARE=0 all
python tools/kanto/gba_rom_audit.py --rom pokeemerald_modern.gba --output gba-rom-audit.json
# libmgba-dev é opcional para o teste de início, nunca obrigatório à ROM:
cc -std=gnu11 -O2 -Wall -Wextra tools/kanto/gba_headless_smoke.c -o /tmp/gba_headless_smoke -lmgba
/tmp/gba_headless_smoke pokeemerald_modern.gba
```

Capturas `gba-boot-frame-*.ppm`, `gba-navigation-frame-*.ppm`, relatório `gba-headless-smoke.txt`. Trata-se de sondagem de introdução, **não** certificado de multiplayer, áudio, combate ou salvamento.

## QA que ainda falta (prioridade)

- P0 sair do caminhão e andar no mapa; testar transições reais, controles, menus, áudio e nova partida.
- P0 usar **save de teste descartável** para salvar, encerrar mGBA, reabrir, validar flags e regressão de Hoenn.
- P0 caminhar Hoenn↔Kanto, mapa Mt. Moon, Rocket, Miguel/fósseis, 8 ginásios, eventos, derrota e retorno.
- P0 observar folga de IWRAM/EWRAM e queda de performance, não apenas o tamanho final da ROM.
- P1 testar multiplayer LAN entre dois PCs e compatibilidade de saves antigos em cópias. Android e hardware físico seguem independentes.
- P1 resolver incompatibilidades restantes `agbcc` somente se o compilador legado voltar a ser um requisito.

## Rollback
PR #61 **draft**. Branch segura V0.24 / PR #62; todos os saves pessoais ficam intocados. Sem merge automático na main. Fonte upstream: https://github.com/pret/pokeemerald/blob/master/INSTALL.md e https://github.com/rh-hideout/pokeemerald-expansion .


### Continuação no commit de diagnóstico do caminhão (24/10/2026)

O [CI #40059442087](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40059442087) gerou ROM ARM GCC válida. As capturas e leitura somente para QA da memória `gSaveBlock1Ptr` mostraram `InsideOfTruck` = mapa 25/40 e posição (2,2), **sem progressão observada até o quadro 45.000**. A caixa de texto das caixas de mudança permaneceu aberta. Isso **não demonstra defeito na movimentação do jogo**, pois a automação apertava botões fora da lógica do diálogo.

A próxima revisão do smoke usa pixels da caixa de diálogo para alternar A e direção direita; armazena o primeiro quadro de movimento e a primeira entrada observada em `LittlerootTown` (grupo 0/mapa 9). Se nenhum desses sinais aparecer, registrar como não verificado, nunca como sucesso presumido. O teste não escreve memória do jogo nem lê saves pessoais.


### Segunda transição do jogo: roteiro do teste (24/10/2026)
O CI #40059886862 (https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40059886862), após corrigir a automatização que reabria o diálogo da caixa, comprovou:
- Quadro **30.240**: primeiro movimento real medido; quadro **30.280**: InsideOfTruck (25/40) mudou para LittlerootTown (0/9).
- O relatório do mGBA registrou littleroot_warp_verified=true e player_movement_verified=true; capturas de 30.400 e 30.900 quadros mostram o protagonista fora do caminhão e a mãe no início do evento.
- Build moderno GBA, Windows Kanto e QA Laboratory SUCCESS na mesma revisão.
- Trata-se de **movimentação, warp e cena inicial** reais; ainda não comprova batalhas, saves ou Kanto completo.

Próxima sondagem (60.000 quadros) avança o diálogo da mãe somente quando a caixa de texto aparece. O script LittlerootTown_EventScript_GoInsideWithMom prepara a transferência automática para LittlerootTown_BrendansHouse_1F (1/0) ou LittlerootTown_MaysHouse_1F (1/2). O teste registrará house_transition_verified somente se realmente observar esses identificadores de mapa na memória do emulador; até o resultado da CI, isso permanece não verificado.
