# Kanto V0.3 — Centros Pokémon e Poké Marts regionais

## Implementação
- Base: `feature/kanto-v02-real-vermilion-exteriors` no commit `3caf970e680487b6d6062f9165a6f772df498bf1`.
- Mantidos os 38 exteriores com layouts de FireRed, tabelas selvagens e barco para Vermilion.
- Ampliados de 2 para **17 interiores de serviços**: Centros Pokémon e Poké Marts em Viridian, Pewter, Cerulean, Lavender, Vermilion, Fuchsia, Cinnabar e Saffron, mais Centro Pokémon em Celadon. Celadon tem Department Store (não foi substituída por Poké Mart fictício).
- Fontes visuais e geometria interiores FireRed: `LAYOUT_POKEMON_CENTER_1F` e `LAYOUT_MART`; não sobrescrevem layouts de Hoenn.
- Portas externas são extraídas da lista original, destinos retornam para o índice local registrado de cada cidade.
- Enfermeiras restauram a equipe via script do Emerald; mercados oferecem estoque genérico inicial enquanto as listas locais exatas de FireRed não são portadas.

## Limites reais
Não foi implementado o segundo andar dos Centros Pokémon (Cable Club continua sendo sistema próprio já existente em Hoenn), eventos de cidade, ginásios, acesso entre cavernas, lojas específicas completas ou save de ponto de cura regional. Os Centros curam, mas **não alteram o último local de cura de Hoenn**; ao perder uma batalha, o retorno pode ser a Hoenn. Não prometer que salvar/reabrir nem todos os acessos foram comprovados em gameplay sem teste real.

## Validação
CI `kanto-v03-regional-services.yml`: testagem estrutural original e cruzada Windows, número de mapas (56), entradas e saídas e comandos da enfermeira/loja. Fazer QA em jogo Windows com saves descartáveis: entrar/sair de todos os edifícios, usar cura e loja, conferir saldo e team, salvar/reabrir de cada cidade, retornar via ferry, comparar com o baseline de Hoenn. Só então avançar para a etapa seguinte.
