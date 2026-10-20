# Kanto V0.5 — travessia por portões de Saffron City

Fonte `pret/pokefirered` pinada em `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`. Base V0.4: `feature/kanto-v04-original-mart-stocks`.

## O que foi desenvolvido

- Os quatro edifícios originais `Route5_SouthEntrance`, `Route6_NorthEntrance`, `Route7_EastEntrance` e `Route8_WestEntrance`, ligados a Saffron City e às quatro rotas.
- Layouts originais 9×11 e 13×9 de FireRed, com blocos, bordas e tileset `gTileset_GenericBuilding2` convertidos ao motor Emerald sem sobrescrever Hoenn.
- Portas **nos dois sentidos**, com remapeamento explícito dos IDs de warp. Não reutiliza cegamente os índices do FireRed, pois mapas de Kanto já receberam warps de Centros e mercados.
- Novos mapas são acrescentados **ao final** de Kanto: os 56 IDs da V0.4 permanecem estáveis. Total do grupo: **60 mapas** (cais de teste + 38 exteriores + 17 serviços + 4 portões).
- O importador preserva o conteúdo anterior, inclusive 8 estoques verdadeiros das lojas e encontros selvagens.

## Limitações

Portões estão sem os NPCs de controle de história originais para permitir testar atravessamento; os diálogos e exigências de acesso devem ser implementados em uma etapa posterior. Permanecem sem integração: Centros 2F, cavernas/dungeons, ginásios, interiores residenciais, rotas subterrâneas, NPCs e campanhas, PokéNav/Fly regional e ponto de whiteout persistente em Kanto. O fechamento de Kanto com 3h+ de jogo **não está comprovado**.

## QA

CI `kanto-v05-saffron-gates.yml` valida layouts, 60 IDs, 4 mapas de portões, correspondência das coordenadas e retorno de cada warp aos exteriores certos, tabelas de estoque e compilação Windows. **Build bem-sucedida não prova transição visível**: testar as quatro rotas ida/volta, sprites/colisões e salvar/reabrir em cópias de saves. Não mesclar PR sem QA.
