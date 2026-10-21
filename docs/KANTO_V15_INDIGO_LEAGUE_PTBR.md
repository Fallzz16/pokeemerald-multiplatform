# Kanto V0.15 — Liga Pokémon e segundo grupo de mapas

Base V0.14 compilada f27fbe991b9f55f8e340c90efd35a9bd4c2a778a. Importação de pret/pokefirered SHA ce6406d8c2eaf46d543c8a2606de0c3cb1951982.

O grupo original gMapGroup_Kanto preserva 107 IDs. O grupo adicionado gMapGroup_Kanto_League contém sete mapas: Centro Pokémon Indigo Plateau 1F, salas de Lorelei, Bruno, Agatha, Lance, Champion e Hall of Fame. Total: 114 mapas Kanto em dois grupos. Não mover IDs antigos de mapas nem flags de save.

Indigo Center tem nurse original na posição fonte (13,10), rotina de cura Emerald e novo KANTO_HEAL_INDIGO_PLATEAU 10. Whiteout reconhece ambos grupos Kanto, preservando último Centro de Hoenn. Segundo andar/link rooms de FireRed são intencionalmente deixados sem warp para proteger LAN.

Limitações: seis salas de Liga têm só geometria e warps; sem Elite Four, Champion, Hall of Fame real, músicas/eventos, narrativa, créditos ou insígnias. A escolha da posição de whiteout 11,15 deve passar por QA visual/colisão do mapa original. Compilação Windows e scripts/warps são testados pela workflow kanto-v15-indigo-league.yml, mas save/reload e LAN/Android exigem teste humano.

160 pickups V0.13 e cinco treinadores permanecem. PR em draft sem merge.