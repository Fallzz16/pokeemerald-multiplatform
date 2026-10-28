# M9 GBA — seletor permanente de NPCs e auditoria de desempenho

**Data:** 27/10/2026. **Escopo:** ROM ARM `.gba`, Pokémon Grand World GBA, PR #102. **Não é o jogo web.** M8/save original permanecem intactos. A escolha feita na introdução é **permanente naquele save**; não há opção de trocar personagens no meio do jogo.

## Fontes primárias pesquisadas

1. Documentação de hardware GBA: https://gbadev.net/gbadoc/memory.html — EWRAM 256 KiB, IWRAM 32 KiB, VRAM 96 KiB e PALRAM; ganhos de RAM são distintos de ganhos de FPS.
2. Gráficos/frame budget: https://github.com/gbadev-org/gbadoc/blob/main/content/graphics.md — 240×160, 59,73 Hz, 280.896 ciclos/frame nominal.
3. Funcionamento das janelas Emerald: https://github-wiki-see.page/m/pret/pokeemerald/wiki/How-Menus-Work-%E2%80%90-Part-1 — charblock de 512 tiles, alinhamento e sobreposição de BG.
4. Original World fixado https://github.com/evilchinesefood/PKMN-World/tree/15d3888b0d81322a04d3c71b0bce18948761ee44 — `src/window.c` mostra `AddWindow()` alocando `32*width*height` bytes de pixel buffer, e `CopyWindowToVram(..., COPYWIN_FULL)` copiando **gráficos + tilemap**; `COPYWIN_GFX` copia somente gráficos.
5. Pokeemerald Expansion https://rh-hideout.github.io/pokeemerald-expansion/FEATURES.html — melhorias recentes de compressão, teste integrado, paletas dinâmicas e visualizador de sprites: **inspiração, não transplante direto de código**.
6. Discussão sobre compressão https://github.com/rh-hideout/pokeemerald-expansion/issues/5169 — `LZ77` pode ser pior para pequenas paletas; codecs experimentais exigem medição, não bastam taxas teóricas.
7. Repositório de sprites/overworld e IDs estendidos https://github.com/EmceeMikey/pokeemerald — há suporte a gráficos OW compactados, mas não se deve substituir o gerenciamento OAM/VRAM já validado da World às cegas.
8. Tutorial de OWEs https://rh-hideout.github.io/pokeemerald-expansion/tutorials/how_to_overworld_wild_encounters.html — compressão `OW_GFX_COMPRESS` afeta VRAM e spawns; preservar a política **FALSE** da M8 que foi explicitamente validada.
9. Auditoria existente `docs/GRANDWORLD_M8_PERFORMANCE_PROFILES.md` — a World M8 já possui perfis de sombras lean/full, guarda otimizada de OWEs e medições OAM corrigidas. **Não** reimplementar o que está aprovado.

## Evidência de falha em execução — antes do reparo

- Workflow https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40508116887 compilou ROM ARM e headless mGBA; **teste Brock falhou 6/9**.
- O menu era aberto, mas após mudar ~26 páginas a rotina recriava/destruía `AddWindow()` e `RemoveWindow()` em todas as mudanças L/R. Uma alocação de 4.608 bytes em `src/window.c:185` terminou em `src/malloc.c:226` com erro real na tela. O cursor não chegou ao NPC esperado, a seleção ficou em CLASSICO e o mapa não carregou; nenhum teste de jogo está homologado.
- Capturas reais e log do erro preservados no workflow; ROM e saves não publicados.
- Outro workflow https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40509620542 **falhou por timeout de instalação apt**, no download da toolchain ARM. Essa falha de infraestrutura **não** é falha compilada nem prova de correção do seletor.

## Melhorias implementadas nesta PR

1. **Sem churn de heap em cada página.** `GW_DrawAvatarChoices(taskId, firstDraw)` chama `AddWindow` exatamente uma vez, mantendo o mesmo buffer ao navegar nas 33 páginas. `GW_CloseAvatarChoices` só desaloca ao confirmar o personagem (A/B).
2. **Buffer menor.** Janela de 12×10 tiles = 120×32 = **3.840 bytes**, contra 12×12 tiles = 4.608 bytes antes do reparo (economia de 768 bytes na alocação do seletor; não alegar 768 bytes livres em todo o jogo). A `baseBlock=360` termina em 480, dentro do charblock de 512 tiles, mantendo FONT_SMALL e seis nomes por página.
3. **Prompt reduzido e posicionamento coerente.** Aproveita `sOutfitPromptWindowTemplate` já existente em `src/oak_speech.c` para mostrar instruções à esquerda. O diálogo antigo do Oak em uma janela 28×15 sobrepunha visualmente o seletor da direita; não usamos mais `OakSpeechPrintMessage` para essa instrução.
4. **Sem duplicação do catálogo na ROM.** `grandworld_avatar_catalog.h` declara `extern` e define os nomes e `sGWAvatarChoices[]` em apenas uma unidade de compilação (`field_player_avatar.c`), sob macro `GW_NPC_AVATAR_DEFINE`. O seletor da introdução só referencia o array. Não afirmar economia numérica até comparar link map/ELF.
5. **Menos DMA ao paginar.** Primeiro desenho usa `COPYWIN_FULL`; os seguintes usam `COPYWIN_GFX`, pois o tilemap de BG não muda. Não copiar 2 KiB extras do mapa BG por página sem necessidade.
6. **Fallback seguro.** Se o seletor ou a janela pequena não forem alocados, continuar com `CLASSICO` sem acessar `WINDOW_NONE` nem modificar a estrutura do save.
7. **Identidade separada.** 192 NPCs humanos da World auditados nas tabelas de gfx, caminhadas e dimensões 16/32; opção 0 é `CLASSICO`. `VAR_GW_NPC_AVATAR` usa o slot VAR 0x40E5 já existente na SaveBlock1, e preserva os seis heróis, gênero, saves e arte de bicicleta/Surf como fallback.
8. **Regressão automatizada.** 9 testes Python específicos; workflow ARM + mGBA verifica Brock (página 26) e Sage (página 32), intro via botões, índice, gênero/herói, sprite vivo no mapa; orçamento do linker usa `tools/grandworld/evaluate_performance_budget.py` existente (reserva de 1 MiB ROM, 8 KiB EWRAM e 2 KiB IWRAM). Relatórios só contam como resultados se o workflow completar com PASS e SHA válido.
9. **Infra CI robustecida.** Timeout do pacote ARM ampliado e `Acquire::Retries`; erro de mirror não deve ser disfarçado de erro de código. Logs de compilação, seções ELF, orçamento e capturas são evidência; ROM/save não vão ao artifact.

## Não mexer às cegas

- Não desabilitar Pokémon selvagens visíveis, seguidores, água, pesca, caverna ou Rock Smash por um ganho estimado de OAM: isso contradiz o objetivo ROM Master.
- Não alterar `OW_GFX_COMPRESS`, padrão de sombras, DMA/IRQ, `-O2`, LTO ou linker sem um teste A/B reprodutível e checagens mGBA; a M8 já tem perfis lean/full.
- Não ativar `-Os` globalmente apenas porque a ROM é grande: medir velocidade/ciclos e footprint para **esta** engine. A ROM é distribuída em 32 MiB padronizados, mas área usada real deve sair do linker.
- Não afirmar que 192 personagens foram todos testados dinamicamente: **192 IDs gráficos validados no código; somente dois casos estão previstos para QA de gameplay**, até aprovação.
- Não afirmar que os 113 slots do Quetzal estão identificados ou importados; o catálogo Quetzal V7 ainda não prova os nomes dos 113 slots.
- Não publicar arte extraída/ROMs de terceiros no GitHub.

## Evidência posterior à falha: gravação verdadeira e orçamento da compilação ARM

**Revisão comprovada:** execução [#40533910470](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40533910470), job concluído com **success** em 27/10/2026. Esta evidência é da revisão executada pelo CI, **não valida automaticamente o HEAD mais recente**.

- **Oito NPCs em emulação real:** NINJA_BOY, AQUA_MEMBER_F, RED, LEAF, BROCK, FALKNER, KIMONO_GIRL e SAGE: 13/13 verificações cada, **104/104** no total. São amostras de gameplay, não 192 avatares validados individualmente.
- **Menu Start e Save real:** o menu de roda tem ícones reordenáveis; o teste passou a escolher a ação Save pelo identificador de ícone **7**, usando `F.selectStartIcon(7)` da biblioteca de QA existente, em vez de um deslocamento fixo. Brock obteve **16/16**, inclusive mantendo o índice de aparência `161` após as entradas Save.
- **Exportação descartável da Flash:** o mGBA produziu um `.sav` de **131088 bytes** em diretório temporário. A execução seguinte iniciou outro processo com o mesmo cartucho ARM e abriu **CONTINUE**: **8/8 verificações**, `VAR_GW_NPC_AVATAR=161`, `graphicsId=302`, identidade e gênero preservados. O arquivo de save foi removido e **não foi publicado** em artifact. Isso resolve o bloqueio relatado na execução #40526880543 para a revisão aprovada.
- **Medição estática real do ELF/GBA:** linker contabilizou `ROM=24.566.120` bytes, `EWRAM=235.264` bytes, `IWRAM=28.200` bytes. Reportou livres `ROM=8.988.312` bytes, `EWRAM=26.880` bytes e `IWRAM=4.568` bytes e aprovou reservas mínimas de 1 MiB ROM, 8 KiB EWRAM e 2 KiB IWRAM.
- **Limite importante:** essa medição é **estática**; não comprova FPS, ciclos/frame, fragmentação de heap em runtime, contagem de sprites ativos, consumo dinâmico de VRAM/OAM nem condições de seguidor + selvagens visíveis. Não extrapolar desempenho dos oito casos sem esses testes.

**Novos gates pendentes no HEAD 033d807a39209144d120f592464bedd323eff93e em 28/10/2026:** testes de CLASSICO, B cancelar, wrap L/R, carregamento de fixture World v7 e repetição do roundtrip Brock. Workflow [#40702048526](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40702048526) encontrava-se em execução durante esta auditoria; consultar o status final antes de declarar esses casos aprovados. Nenhuma alteração da M8 estável ou da biblioteca privada Quetzal foi feita neste registro.

## Próximos gates objetivos

- Validar os 9 testes Python, o `make modern` da ARM e o relatório de orçamento real do linker na MESMA revisão de fonte. Todo job tem que estar verde.
- Inspecionar screenshots do menu inicial e das páginas 26 e 32. Confirmar que ambos os personagens estão **visíveis** e que o jogador usa `graphicsId` correto no hub. Reprovar fundos/strings ocultas, mesmo com flags em estado válido.
- Testar gravação/Continue real, retorno de Surf/bicicleta, follower + Pokémon visível (OAM/VRAM) e compatibilidade com save anterior antes de mesclar. A inclusão do seletor no jogo é opcional; não travar saves antigos.
- Só depois ampliar Quetzal e medir gráficos/economia efetiva de ROM em famílias reais.

**Status:** documentação das alterações de código aplicadas; não é prova de sucesso da revisão atual no mGBA.
