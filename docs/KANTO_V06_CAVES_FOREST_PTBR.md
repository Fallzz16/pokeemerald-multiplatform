# Kanto V0.6 — Viridian Forest, Mt. Moon e Diglett's Cave

## Escopo e origem
- Base segura: V0.5, commit `26c4c61d070804663e88fcac875904855f4c4089`, workflow específico aprovado.
- Fonte: `pret/pokefirered` pinada em `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`.
- Nova branch `feature/kanto-v06-forest-moon-diglett`, PR para a V0.5.

## Implementado em código
- **9 mapas adicionais** do original: ViridianForest, Route2_ViridianForest_NorthEntrance, Route2_ViridianForest_SouthEntrance, DiglettsCave_NorthEntrance, DiglettsCave_B1F, DiglettsCave_SouthEntrance, MtMoon_1F, MtMoon_B1F e MtMoon_B2F.
- Os nove layouts, blocos e bordas são copiados da revisão FireRed e os tilesets de ViridianForest, DiglettsCave e Cave são convertidos conforme os limites FRLG 640/7, sem alterar os recursos de Hoenn.
- Todas as saídas originais desses mapas para os outros nove mapas e Route2, Route4 ou Route11 são ligadas, com remapeamento de IDs de warp externos e validação de todas as referências.
- Encontros selvagens de FireRed (não LeafGreen) nesses mapas são acrescentados aos exteriores já importados.
- **Total: 69 mapas de Kanto registrados**, incluindo o cais antigo; os primeiros 60 mapas mantêm exatamente a ordem anterior e os novos mapas são acrescentados ao final.
- A compilação Windows e o relatório de dados são produzidos pela workflow `kanto-v06-forest-moon-diglett.yml`, com checagem de byte hash dos nove blocos, dimensões, destinos e retorno de warps e tabelas selvagens.

## Limites verificáveis
- **NPCs, treinadores, fósseis, itens, eventos de história e batalhas roteirizadas dessas áreas ainda não são importados.** São geometria autêntica, warps e Pokémon selvagens, não a campanha completa de FireRed.
- A travessia depende de colisão e metatile behaviors: efeitos especiais e tile animations seguem pendentes de teste visual real.
- O jogador ainda não possui ponto próprio de whiteout / save de Centro Pokémon em Kanto validado. Use cópias de saves.
- A rede, Android e o conteúdo de mais de três horas não foram certificados. O CI comprova compilação e consistência dos dados, **não** gameplay sem bugs.
- Rollback M2.2-B `5e53e40`, PRs anteriores mantidas abertas e não mescladas.

## Próximos objetivos
Importar eventos, encontros de treinadores e objetos de Viridian Forest/MtMoon; estabilizar cura, respawn e saves próprios por região; portar Rock Tunnel e conexões das rotas; executar QA manual de caminhada, batalha, captura e save/reload antes de declarar o primeiro conjunto totalmente jogável.
