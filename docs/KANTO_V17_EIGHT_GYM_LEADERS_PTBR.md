# Kanto V0.17 — oito líderes de ginásio com flags isoladas

Base: Kanto V0.16 compilado `243fe418466c32a56bf0c5581fe01fbb7de4c8c1`. Fonte FireRed pinada no commit `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`.

O importador agora acrescenta Koga (Fuchsia), Sabrina (Saffron), Blaine (Cinnabar) e Giovanni (Viridian) aos primeiros quatro líderes. Os oito ginásios têm NPC de líder em posição original, equipes, níveis, golpes e itens de treinador verdadeiros de FireRed, **mas sprites/retratos de Emerald continuam provisórios**. Incluídos badges próprios (SOUL, MARSH, VOLCANO, EARTH) e TMs originais (06/Toxic, 04/Calm Mind, 38/Fire Blast, 26/Earthquake). Recompensas possuem flags que evitam recebimentos repetidos.

## Arquitetura de treinador sem expandir saves

O save original reserva exatamente **864 bits para vitórias de treinadores**; V0.16 já utiliza os IDs 0–863. Para não aumentar SaveBlock nem ocupar flags Hoenn, `src/battle_setup.c` adiciona `GetTrainerSaveFlag(id)`. IDs antigos 0–863 mantêm a mesma fórmula original; os novos líderes 864–867 usam quatro flags que eram `FLAG_UNUSED_0x...`. Todos os acessos relevantes (primeiro/segundo adversário, leitura de script, vitória, consulta e limpeza) passam por essa tradução. O array de dados de treinadores cresce a `TRAINERS_COUNT=868`, mas `MAX_TRAINERS_COUNT=864` **permanece igual**; não mexer nessa constante por causa do tamanho do save.

O registro automático de 12 novas flags (4 derrotas, 4 insígnias, 4 TM) ocorre depois dos 160 pickups e das oito flags das quatro primeiras insígnias/recompensas, com comparação de unicidade. A ordem de mapas (114 em dois grupos) permanece intacta.

## Limites críticos
- O mapeamento de treino é explícito **apenas para IDs 864–867**. Outros treinadores ainda exigem alocação e extensão consciente da tabela, sem reordenar IDs anteriores.
- Conteúdo de puzzles e scripts de história (Silph Co./Rocket/Giovanni), sprites de FireRed, diálogos originais e animações especiais pendentes.
- QA real de batalhas, vitória/derrota, repetição, badges após save/load, Itemfinder, whiteout e multiplayer/Android precisa acontecer com saves descartáveis antes de merge. CI automatizado não garante gameplay correto.
- Oito líderes com suas equipes importados **não significa oito ginásios originais totalmente concluídos**: puzzles, NPCs comuns e progressão continuam faltando.
