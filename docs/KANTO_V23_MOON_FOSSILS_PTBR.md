# Kanto V0.23 — Miguel e escolha exclusiva dos fósseis de Mt. Moon

Branch: feature/kanto-v23-mtmoon-fossil-choice, a partir da PR #59 V0.22, base f06a8441029b7e11955151fc3ccded3d2acaa6df.
Fonte FireRed fixa: ce6406d8c2eaf46d543c8a2606de0c3cb1951982.

## Gameplay integrado ao código gerado
- Super Nerd Miguel de FireRed aparece nas coordenadas originais MtMoon_B2F (13,11), com a equipe original Grimer, Voltorb e Koffing de nível 12. Trainer ID 904 e vitória persistente flag 0x90C.
- Fossil Dome (13,7) e Fossil Helix (14,7) importados com gráficos OBJ_EVENT_GFX_FOSSIL originais, disponíveis em Emerald.
- Enquanto Miguel não foi derrotado, os fósseis não podem ser recebidos. Após vitória, o jogador escolhe apenas um, com mensagem SIM/NÃO.
- A entrega usa giveitem e só registra a opção quando VAR_RESULT é verdadeiro. Mochila cheia permite repetir sem consumir a escolha. Escolher Dome registra 0x90E; escolher Helix registra 0x90F. Ambos gravam 0x90D de conclusão.
- Os dois objetos têm a mesma flag de ocultação 0x90D e desaparecem de forma persistente após uma transição. Na tela da coleta, o objeto escolhido é removido; o outro pode permanecer desenhado até a saída do mapa, mas é protegido por script contra segunda coleta. Esse acabamento visual ainda precisa ser trabalhado.
- FireRed Super Nerd não tem classe/retrato nativos nesta base Emerald: campo OBJ_EVENT_GFX_SCIENTIST_1 e retrato de Collector são substitutos TEMPORÁRIOS. Falas e movimentos da história são provisórios, não toda a sequência original.
- Nenhum ID de mapa, flag antiga ou save foi modificado. O total gerado previsto é 50 NPCs de batalha (8 líderes +42 comuns), 221 flags alocadas em Kanto, 114 mapas e 160 pickups anteriores.

## Saves e rollback
- Trainer ID 904 é traduzido em GetTrainerSaveFlag para a flag salva 0x90C. Os demais bits novos 0x90D..0x90F pertencem a SYSTEM_FLAGS, anteriores às flags diárias 0x920. MAX_TRAINERS_COUNT continua 864; TRAINERS_COUNT passa a 905 só nos dados gerados.
- A soma de 217 flags anteriores + 4 novas é 221; restam 16 bits na faixa conservadora 0x910–0x91F. Não expandir MAX_TRAINERS_COUNT nem modificar SaveBlock.
- PR inicial em draft; rollback para PR #59 V0.22 f06a8441029b7e11955151fc3ccded3d2acaa6df e instalar em diretório novo sem sobrescrever saves.

## Testes e estado
- Importador tools/kanto/v23_moon_fossils.py valida a fonte FireRed, party, colisões de NPC, símbolos e limites de flags.
- tests/test_kanto_v23_moon_fossils.py garante fidelidade das três posições, único fossil possível, item só após Miguel, comportamento de bag full por inspeção de scripts, flags distintas e compatibilidade do save.
- .github/workflows/kanto-v23-moon-fossils.yml mantém regressões V0.19/V0.20/V0.21/V0.22, topologia de mapas, todas as importações e cross-build Windows.
- Workflows e artefatos devem ser avaliados no HEAD exato. CI verde é geração e compilação, NÃO teste humano do script, persistência após salvar/recarregar, câmera, colisions, LAN ou Android.

## O que ainda falta
Verificação real da batalha Miguel, sequência de duas opções, mochila cheia, flags após save/close/reload e retorno Hoenn; sprites corretos da Equipe Rocket/Miguel, movimentações originais e desaparecimento instantâneo do segundo fóssil. Mais eventos Mt. Moon, S.S. Anne, Silph Co., Team Rocket, puzzles, Elite Four, Hall of Fame, PokéNav/Fly, música, rede em Kanto, Android e QA dos saves. CI legado GBA separado.
