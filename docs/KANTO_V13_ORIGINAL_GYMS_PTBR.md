# Kanto V0.13 — geometria dos oito Ginásios de FireRed

Fonte reprodutível: `pret/pokefirered` (SHA `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`), sobre a V0.12 aprovada (`6444892bfcaf667538abe8cb33fd1047dd3118b9`).

## Código implementado
- Importação dos oito edifícios: Viridian, Pewter, Cerulean, Vermilion, Celadon, Fuchsia, Saffron e Cinnabar.
- Cada ginásio tem layout, dimensões, blockdata, bordas e tileset secundário originais. `gTileset_KantoBuilding` mantém a geometria de FireRed dentro do motor Emerald, com divisão de tiles e paletas Kanto.
- Entradas originais são conectadas às oito cidades. Saídas voltam ao mapa exterior com índices de warp remapeados. Os **30 teletransportes internos** de Saffron mantêm os pares originais.
- Os oito mapas são **acrescentados apenas depois dos 99 mapas V0.12**, garantindo estabilidade de IDs dos mapas anteriores.
- Nenhum ID/flag de save anterior, item visível/oculto ou sistema de Hoenn foi alterado.

## Limites: ainda não são Ginásios jogáveis completos
- Líderes, Pokémon/equipes, treinadores, scripts e insígnias não migrados.
- Mecanismos do Vermilion Gym, obstáculos de Fuchsia e outras ações roteirizadas não estão homologados.
- As portas e teletransportes são dados de mapa válidos; falta testar cada passagem e colisão no executável.
- Ainda não há campanha Pokémon FireRed completa, PokéNav/Fly regional, música e animações originais, nem QA de save Android/LAN.

## Gates de qualidade
CI `kanto-v13-original-gyms.yml`: compara blocos reais byte-a-byte, layouts, 107 registros, integridade de destinos/retornos e índice dos teletransportes, 119 flags originais, cura, itens, treinadores anteriores, build Windows. O estado é **preview experimental**; não mesclar sem jogar e testar os oito prédios.

Próximas fases: lógica de ginásio fiel, badges regionais separados, escalabilidade de flags de treinador (restam apenas 4 slots já reservados), validação de salvamento e batalhas reais, regiões/áreas especiais e LAN/Android.
