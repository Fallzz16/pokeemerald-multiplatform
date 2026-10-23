# Kanto V0.21 — primeiro evento Rocket na Ponte Nugget (Route 24)

Base V0.20 PR #57, commit 3d3df41797dac5af218969161ac1c7462f587937.
Fonte FireRed fixada em ce6406d8c2eaf46d543c8a2606de0c3cb1951982.

## Implementado
- NPC Rocket original de Route24 (12,15) com gráfico de campo original OBJ_EVENT_GFX_MAN.
- Equipe FireRed original sParty_TeamRocketGrunt6 (Ekans e Zubat, nível 15). O retrato de batalha usa Team Aqua de Emerald PROVISORIAMENTE: não é o retrato Rocket original.
- Trainer ID append-only 899; FLAG_KANTO_V21_BRIDGE_ROCKET_DEFEATED = 0x906.
- Nugget com flag independente de recebimento FLAG_KANTO_V21_BRIDGE_NUGGET_CLAIMED = 0x907. Código só confirma a flag depois da entrega; se a mochila está cheia, permite tentar novamente.
- Ordem provisória batalha -> Nugget, diferente de FireRed, que entrega a recompensa antes de enfrentar o agente. Falas curtas provisórias.
- Sem novos mapas. Total esperado 45 treinadores e 213 flags reservadas de Kanto. Preserva as 211 anteriores; 0x906 e 0x907 são SYSTEM_FLAGS persistentes, anteriores ao início diário em 0x920. MAX_TRAINERS_COUNT = 864 não muda; TRAINERS_COUNT gerado = 900. Sobram 24 bits conservadores no intervalo 0x908..0x91F.

## Testes e limitações
- tools/kanto/v21_rocket.py valida origem, equipe, ausência de colisão, flags e limites de save antes de emitir alterações.
- tests/test_kanto_v21_nugget_bridge.py confere ator, party, entrega única, tratamento de mochila cheia e flags persistentes.
- Workflows V0.21 compilam Windows depois de importar o FireRed pinado. Não afirmar resultados antes do sucesso verificado no SHA final.
- Não é homologação humana de batalha, vitória/derrota, item, reload, animações, colisão, LAN ou Android.

## QA de aceitação
Usar pasta Windows experimental e cópias de saves; entrar Route24, falar com Rocket, perder e vencer, verificar mochila cheia e prêmio uma vez, salvar/reabrir e garantir vitória/prêmio persistentes. Verificar os seis treinadores de Route24, Hoenn e rede.

Continuam faltando Rocket de Mt. Moon, Silph Co., outros eventos da história, fósseis, S.S. Anne, Elite Four, puzzles, retratos e animações originais, PokéNav/Fly, multiplayer e Android.
PR draft separada; sem merge em main. Rollback seguro para V0.20 PR #57, nunca sobrescrever arquivos sav.