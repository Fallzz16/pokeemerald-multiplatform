# Pokémon Emerald Hybrid — Kanto: decisões 1–40 (2026-10-20)

## Respostas literais e escopo da rodada

`1C 2A 3D 4A 5A 6B 7C 8C 9A 10B 11D 12A 13B 14A 15D 16C 17D 18B 19B 20C 21A 22A 23A 24A 25A 26A 27A 28C 29A 30A 31A 32D 33D 34D 35D 36D 37D 38D 39D 40D`

**40/250 respondidas:** 27 alternativas específicas (A/B/C) e 13 delegações técnicas (D).
**Perguntas 41–250 permanecem SEM RESPOSTA** — não presumir D nem escolher por conta própria com base neste questionário. Continuam válidas as decisões anteriores do Emerald Hybrid relacionadas a multiplayer, Brendan/May, backups, versões Windows/Android e salvamento.

## Interpretação vinculante

| Questões | Decisão |
|---|---|
| 1C, 7C, 8C | Alvo inicial ambicioso: várias cidades ao mesmo tempo, quase toda Kanto explorável e mais de 3 horas de jogo (ainda NÃO implementado) |
| 2A | Para chamar de jogável, testar exploração, batalhas, cura e save |
| 3D, 11D, 15D, 17D | Delegadas: manter viagem de barco e cancelamento antes do embarque; retorno seguro |
| 4A, 5A | Equipe/progresso atual do treinador; campanhas Hoenn e Kanto independentes |
| 6B, 18B | Viagem após quatro insígnias, dependente de progresso |
| 9A, 10B | Windows offline primeiro, desenvolvimento equilibrado |
| 12A | Transição simples, sem animação longa |
| 13B, 14A | Tarifa fixa e confirmação: valor técnico provisório **P500**, ainda não escolhido pelo usuário |
| 16C | Destino final direto na cidade de chegada, preferencialmente Vermilion; cais atual é provisório |
| 19B | Voltar ao último Centro Pokémon de Hoenn: **pendente**, K0 ainda retorna a Slateport |
| 20C | Falha de viagem deve ter fallback na cidade inicial segura: **pendente**, evitar qualquer warp inválido primeiro e jamais sobrescrever save silenciosamente |
| 21A–26A | Layout e geografia originais de FireRed, mesmas posições, medidas, conexões, cavernas e florestas |
| 27A | Áreas originais Hybrid só depois de converter Kanto |
| 28C | Importar **todos os exteriores antes dos interiores**; não liberar exteriores visualmente incompletos no jogo |
| 29A | Sevii Islands em uma etapa posterior |
| 30A | Kanto antes da conclusão de Hoenn, compatível com o desbloqueio após quatro insígnias |
| 31A | Aparência FireRed original |
| 32D–40D | Delegadas: preservar gráficos originais e evitar mexer nos tilesets de Hoenn; priorizar compatibilidade do renderizador atual |

## Desenvolvimento sem anúncios prematuros

A base K0 está na PR #24 (`feature/emerald-kanto-gateway-m0`); cais provisório Kanto, ida/volta em Slateport e validação estrutural/cross-build, ainda sem QA humano.

A branch `feature/kanto-v01-decisions-import-preflight` acrescenta:
- Filtro `FLAG_BADGE04_GET` no marinheiro em Slateport (quarta insígnia da sequência normal de Hoenn).
- Tarifa fixa **P500**, descontada só após confirmar SIM e passar `checkmoney`. O botão NÃO, insígnias insuficientes e saldo insuficiente não descontam dinheiro.
- `tools/kanto/preflight.py`: **leitura somente** da fonte exata `pret/pokefirered` no commit `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`. Seleciona somente as cidades principais e rotas exteriores originais, excluindo Sevii. Verifica o `map.bin`, dimensões, borda e referências e produz um relatório JSON de impedimentos por mapa; **não transfere nenhum binário para o jogo**.
- Testes `tests/test_kanto_gateway.py` e `tests/test_kanto_preflight.py`, CI `.github/workflows/kanto-v01-preflight.yml` e compilação cruzada Windows condicionada a testes do auditor.

### Como executar o levantamento com dois repositórios clonados

```bash
python tools/kanto/preflight.py --firered /caminho/pokefirered --emerald . --output kanto-preflight.json
```

O workflow baixa o código-fonte público de FireRed em uma revisão pinada. Quando executar, consultar seu relatório e logs reais, não inferir resultados.

### Fases até o primeiro jogo jogável de verdade

1. **Conversão estrutural:** portar graficamente o mapa externo original, com paletas, tilesets, metatiles, elevação e colisões. Não copiar `map.bin` cru sem compatibilizar índices de tiles. Manter Hoenn intacta.
2. **Superfície Kanto:** registrar todos os exteriores previstos em uma área de teste; confirmar bordas/portas/conexões reais, originário FireRed, sem substituir mapas Emerald. Conectar Vermilion e mudar destino do barco somente após área real validada.
3. **Sistemas mínimos jogáveis:** interiores essenciais, cura, encontros, treinadores, dinheiro, texto de viagem, salvamento e carregamento, retorno ao último Centro Pokémon de Hoenn, recuperação segura. Fazer teste com cópias isoladas de saves.
4. **QA real:** ZIP Windows com SHA exato, gráficos 240x160, jogo executável e testes humanos de caminhar, combater, capturar, salvar/recarregar e voltar. Confirmar desempenho e roteiro de >3 horas de conteúdo antes de declarar meta 7C/8C cumprida. Testar LAN e Android após baseline Windows.

### Ainda NÃO concluído
Importação de cidades originais, tilesets FireRed, mapas com colisões reais, cenários jogáveis de 3+ horas, sistema de retorno ao Centro Pokémon de Hoenn (#19B), recuperação de viagem (#20C), ginásios, NPCs e salvamento validado em Kanto. O porto K0 ainda é Emerald provisório. **Não existe novo ZIP comprovadamente jogável desta alteração antes de CI e QA reais.**

**Rollback:** branch funcional histórica M2.2-B commit `5e53e40`; PR #19 e PR #24 intocadas. Não modificar o save original nem usar hacks de offsets para teletransporte.
