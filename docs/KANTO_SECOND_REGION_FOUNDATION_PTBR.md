# Kanto como segunda região — incremento K0 (porto de chegada)

**Estado:** implementação inicial de um porto de teste, NÃO importação do continente completo.
**Origem:** `pret/pokefirered`, referência de estudo; nenhuma pasta/binário de FireRed foi copiado neste incremento.
**Branch isolada:** `feature/emerald-kanto-gateway-m0`, derivada de `feature/emerald-v100-m23a-server-first-lab` no commit `59b94d1a6b2411f85b0eac8a12d31cb7b92fc73f`.
**Compatibilidade:** Windows/Android ainda exigem compilação e QA real para este novo HEAD.

## Objetivo aprovado
Hoenn permanece como jogo principal. Kanto será uma região própria, acessível por barco, mantendo o mesmo treinador, inventário e save. O mapa real de Kanto (Pallet Town, cidades, rotas, interiores e conexões) será importado em lotes, sem sobrescrever Hoenn.

## Alteração concreta K0
- Acrescentado **`gMapGroup_Kanto` ao fim de `group_order`** para preservar os IDs existentes dos grupos que ficam antes dele.
- Criado o mapa `Kanto_Harbor` com `LAYOUT_ISLAND_HARBOR` (layout **já existente do Emerald**, provisório).
- No porto de Slateport, novo marinheiro com pergunta SIM/NÃO; SIM viaja a `MAP_KANTO_HARBOR`; NÃO mantém o jogador no local.
- No cais de chegada, outro marinheiro permite retornar ao mesmo porto de Slateport.
- Os scripts antigos de S.S. Tidal, Battle Frontier e ticket de eventos não foram alterados. Nenhum offset de save foi adulterado.
- O porto **não inclui cidade, rota, Pokémon selvagens, Poké Center, Poké Mart ou o desenho original de Kanto**. É apenas uma área de verificação da transição entre grupos.

## Integração progressiva do mapa real

1. **K1: migração de tilesets** (paletas, metatiles, colisão/elevação e formatos FireRed x Emerald). Criar versões compatíveis, sem substituir tilesets globais de Hoenn.
2. **K2: primeiro trecho real:** mapa externo de Vermilion City/porto, depois conexões para Route 6/11 e interior; substituir o destino do barco somente após testar colisão, limite de câmera e warps.
3. **K3: continente:** Pallet Town, Viridian, Pewter, Cerulean, Lavender, Celadon, Saffron, Fuchsia, Cinnabar e rotas/cavernas/interiores ligados, conferindo coordenadas de saída e conectividade.
4. **K4: sistemas:** nomes e mapa regional próprios, voo/teleporte, pesca, surf, encontros, NPCs, scripts, ginásios e eventos de história adaptados. Evitar conflitos de flags/vars, heal locations, músicas e Pokedex.
5. **K5: multiplayer:** dois jogadores atravessando grupos, câmera/sprites corretos ao entrar/sair, backups e persistência de coordenadas. Android/Windows testados separadamente.

## QA K0 obrigatório
- `python -m unittest discover -s tests -p test_kanto_gateway.py -v` (verificações estáticas).
- Compilar a versão nativa Windows com o fluxo já documentado no projeto; checar IDs gerados pelo `mapjson`, montagem de scripts, linkedição e inicialização.
- Em cópia de save de teste: entrar no porto de Slateport, encontrar novo marinheiro, aceitar a viagem, caminhar no porto Kanto, recusar e depois aceitar a volta; repetir após salvar e carregar.
- Confirmar que S.S. Tidal, evento de tickets, Cable Club, solo, EHL8 e sprites continuam funcionando. Em multiplayer, cada treinador preserva sua localização individual.
- **Pendente:** teste de colisão manual no tile do novo marinheiro em Slateport (x=14,y=12) e teste gráfico de Kanto Harbor. Se o NPC não estiver alcançável, reposicionar pelo editor Porymap **antes** de mesclar.
- Falha em build ou QA: não mesclar. Branch original `feature/emerald-v100-m23a-server-first-lab` permanece intocada; rollback M2.2-B no commit `5e53e40`.

## Limitações atuais
- O mapa de Hoenn exibido no PokéNav ainda não alterna para Kanto.
- A seção provisória do porto é `MAPSEC_NONE`; nome regional verdadeiro será adicionado com a expansão.
- O porto usa arte/layout Emerald, não a geografia exata de FireRed. **Não declarar Kanto completa/jogável.**
