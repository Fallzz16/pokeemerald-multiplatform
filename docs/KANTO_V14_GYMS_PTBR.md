# Kanto V0.14 — os oito ginásios originais como edifícios

Derivação: V0.13 (33 bolas + 8 itens escondidos extras em 99 mapas). Cópia de blocos, bordas, metatiles e tilesets de FireRed pinned ce6406d8c2eaf46d543c8a2606de0c3cb1951982.

Mapas: Viridian, Pewter, Cerulean, Vermilion, Celadon, Fuchsia, Cinnabar e Saffron Gyms — oito novos interiores adicionados aos IDs 99–106, passando a 107 mapas de Kanto. As portas originais ligam os ginásios às respectivas cidades e Saffron Gym inclui os warps internos originais de teleporte.

**Não inclui** treinadores, líderes, falas, insígnias, TM de recompensa, requisitos de história, puzzles, interruptores ou barreiras; portanto NÃO é possível concluir ginásios nesta versão. É um marco geométrico preparatório, não o sistema de ginásios pronto.

Proteções: 99 IDs antigos e 160 flags de itens preservados; script de importação continua reproduzível, compilação Windows específica em kanto-v14-eight-gyms.yml. Testar em jogo com save descartável: portas, passabilidade e não ficar preso nos portais, especialmente Saffron. Nada mesclado à versão principal.

## Limites técnicos auditados
A numeração dos mapas usa índices com representação de 8 bits. O importador agora falha explicitamente se o grupo Kanto exceder 128 entradas (índices 0–127), evitando corrupção silenciosa em novos warps. Com 107 mapas, restam 21 posições nesse grupo. A próxima expansão grande deverá adicionar **um novo grupo Kanto**, sem deslocar os 107 IDs já usados em saves. Também restam apenas quatro dos nove espaços reservados de treinador; não portar novas dezenas de treinadores sem solução de persistência.
