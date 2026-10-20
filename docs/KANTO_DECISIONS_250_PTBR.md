# Emerald Hybrid — decisões definitivas de Kanto (250/250)

Recebido em 2026-10-20. A especificação anterior de 40 respostas foi substituída por esta versão. **34 escolhas específicas, 216 decisões técnicas delegadas (D); 0 perguntas em aberto.**

## Respostas, literalmente
```
1C 2A 3D 4A 5A 6B 7C 8C 9A 10B 11D 12A 13B 14A 15D 16C 17D 18B 19B 20C
21A 22A 23A 24A 25A 26A 27A 28C 29A 30A 31A 32A 33A 34A 35A 36D 37A 38A 39D 40A
41D 42D 43D 44D 45D 46D 47D 48D 49D 50D 51D 52D 53D 54D 55D 56D 57D 58D 59D 60D
61D 62D 63D 64D 65D 66D 67D 68D 69D 70D 71D 72D 73D 74D 75D 76D 77D 78D 79D 80D
81D 82D 83D 84D 85D 86D 87D 88D 89D 90D 91D 92D 93D 94D 95D 96D 97D 98D 99D 100D
101D 102D 103D 104D 105D 106D 107D 108D 109D 110D 111D 112D 113D 114D 115D 116D 117D 118D 119D 120D
121D 122D 123D 124D 125D 126D 127D 128D 129D 130D 131D 132D 133D 134D 135D 136D 137D 138D 139D 140D
141D 142D 143D 144D 145D 146D 147D 148D 149D 150D 151D 152D 153D 154D 155D 156D 157D 158D 159D 160D
161D 162D 163D 164D 165D 166D 167D 168D 169D 170D 171D 172D 173D 174D 175D 176D 177D 178D 179D 180D
181D 182D 183D 184D 185D 186D 187D 188D 189D 190D 191D 192D 193D 194D 195D 196D 197D 198D 199D 200D
201D 202D 203D 204D 205D 206D 207D 208D 209D 210D 211D 212D 213D 214D 215D 216D 217D 218D 219D 220D
221D 222D 223D 224D 225D 226D 227D 228D 229D 230D 231D 232D 233D 234D 235D 236D 237D 238D 239D 240D
241D 242D 243D 244D 245D 246D 247D 248D 249D 250D
```

## Requisitos prioritários invioláveis
- Kanto como segundo continente, Hoenn intacta, mesmo treinador e equipe, campanhas distintas.
- Fidelidade geográfica ao FireRed de GBA: cidades, dimensões, rotas, cavernas, conexões, estradas, árvores, praias, edifícios e decoração originais (21–27 e 31–35, 37, 40 = A).
- Importar os **exteriores primeiro** (28C), Sevii numa etapa posterior (29A).
- Quase toda a superfície de Kanto, várias cidades em primeiro marco, >3h de conteúdo real quando se declarar jogável (1C, 7C, 8C).
- Liberação após quatro insígnias (6B), passagem fixa (13B), confirmação (14A), desembarque direto na cidade (16C), última cura em Hoenn como destino de volta (19B, ainda não pronta) e recuperação segura conforme 20C (ainda não pronta).
- A primeira jogabilidade precisa incluir andar, batalhar, curar, salvar (2A); Windows offline primeiro (9A). Equilíbrio entre segurança e velocidade (10B).
- Escolhas D delegam apenas decisão técnica: priorizar adaptação fiel, persistência segura, QA por fase, comunicação multiplayer preservada, importação versionada, não prejudicar nenhuma instalação antiga.

## Marcos de engenharia
K0: antigo cais Emerald com retorno e tarifa (PR #24 e #25).
K1: **geometria exterior FRLG** + tilesets e paletas originais, sem NPCs/warps interiores nem batalha/cura. É precursor real, mas NÃO jogável no sentido de 2A.
K2: conexões validáveis, colisões corrigidas, portas, Centro Pokémon e cura, NPCs básicos, encontro/batalha, retorno Hoenn e save protegido. Só então declarar primeira área realmente jogável.
K3: alargar e validar o restante do continente com encontros, eventos, cavernas, ginásios e traduções.
K4: multiplayer no mesmo mapa e Android após QA Windows, PokéNav/Kanto/Fly regional, testes de saves antigos.
Rollbacks: M2.2-B `5e53e40`; PR #19, #24, #25 não alterar diretamente.
