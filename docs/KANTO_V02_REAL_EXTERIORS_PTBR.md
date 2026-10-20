# Kanto V0.2 — conversão dos exteriores reais de FireRed

Fonte: `pret/pokefirered` commit `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`.
Branch: `feature/kanto-v02-real-vermilion-exteriors` (PR encadeada sobre #25).

## Execução local
Com os dois repositórios em discos locais:
```bash
python tools/kanto/import_exteriors.py --firered ../pokefirered --emerald . --report kanto-exteriors-import.json
make -f Makefile_pc
```

O importador materializa os **38 exteriores** do FireRed (excluindo as Sevii), usando `map.bin`, `border.bin`, artes `tiles.png`, paletas e metatiles da revisão pinada. Cria grupo Kanto, constante específica para cada mapa e converte o formato de atributos metatiles FR 32 bits para o do Emerald 16 bits, aplicando alias de comportamentos e registrando desconhecidos.

O motor agora seleciona limites **640 tiles/metatiles e 7 paletas primárias** quando a primeira tileset é `gTileset_KantoGeneral`, preservando o split original 512/6 em todos os mapas de Hoenn. Recursos são gerados em diretórios isolados; nunca sobrescreve os tilesets originais de Hoenn.

A viagem paga por quatro insígnias muda para a verdadeira **Vermilion City**. Sua equipe, bag e estado do save são mantidos por usar o motor Emerald. O NPC de retorno leva provisoriamente a Slateport. A saída para último Centro Pokémon de Hoenn (#19B) e fallback cidade inicial (#20C) precisam implementação dedicada e QA.

## PENDÊNCIAS QUE IMPEDEM chamar versão completa ou jogável
- Não são importados interiores, curas, NPCs/treinadores originais, ginásios, missões, encontros selvagens e música original.
- Portas internas continuam sem warp intencionalmente para evitar entrar em mapas não importados. A maioria das rotas externas se conecta, mas travessias por cavernas/portões podem bloquear progresso.
- Alguns comportamentos de metatiles não existem nativamente no Emerald; o relatório lista conversões desconhecidas e devem ser validadas, sem prometer colisão idêntica.
- Em mapas FireRed com animações próprias de tiles, o importador inicialmente usa `callback=NULL` e gráficos estáticos. Ainda exige inspeção visual.
- O ZIP gerado por CI contém somente preview da geometria, não substitui versão funcional nem implica 3h de aventura.
- Save manual e LAN/câmera, velocidade e Android exigem testes com saves descartáveis em Windows antes de merge.
