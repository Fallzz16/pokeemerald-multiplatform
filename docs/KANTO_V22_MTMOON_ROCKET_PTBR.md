# Kanto V0.22 — quatro agentes da Equipe Rocket em Mt. Moon B2F

Continua a linha V0.21 PR #58, base exata d2551149cdb949602f3cbcfdc0d29dd0f404c0d7.
FireRed fonte fixada: ce6406d8c2eaf46d543c8a2606de0c3cb1951982.

## O que foi implementado
- Quatro batalhas com os Grunts Rocket originais da fonte FireRed em MtMoon_B2F: Grunt1 (12,20), Grunt2 (18,27), Grunt3 (35,12), Grunt4 (37,21). Seus dados de nível, espécies e equipes são copiados integralmente da fonte fixada.
- Movimento, alcance de visão e coordenadas dos quatro atores são preservados. FireRed OBJ_EVENT_GFX_ROCKET_M não existe no Emerald Hybrid: campo usa temporariamente OBJ_EVENT_GFX_AQUA_MEMBER_M; batalha usa classe/retrato de Team Aqua masculina.
- Scripts trainerbattle_single com diálogos provisórios, sem afirmar roteiro Rocket, eventos de fósseis e Giovanni completos.
- Trainer IDs estáveis 900–903 e quatro flags permanentes 0x908–0x90B, adicionais às 213 flags da V0.21 e anteriores às flags diárias 0x920.
- TRAINERS_COUNT=904 após geração, MAX_TRAINERS_COUNT=864 e SaveBlock originais preservados. Totais previstos: 49 NPCs de batalha (8 líderes, 41 comuns), 217 flags Kanto de conteúdo e 114 mapas antigos. Restam 20 bits conservadores 0x90C–0x91F.

## QA e limitações
- Novo tools/kanto/v22_rocket_moon.py valida FireRed original, position/sight, party e species, duplicatas e faixa persistente antes de modificar o materializado.
- tests/test_kanto_v22_moon_rocket.py testa quatro atores, equipes byte a byte, flags, números de treinador e ausência de colisões.
- Testes V0.19/V0.20/V0.21 permanecem e aceitam novos trainers, sem remover asserções de compatibilidade.
- Workflow .github/workflows/kanto-v22-moon-rocket.yml: importa fonte pinada, executa QA histórico e novo, verifica grafo e compila Windows. O resultado deve ser verificado no SHA final; build não é gameplay.
- Nenhum save pessoal foi aberto ou alterado. PR draft sem merge, rollback V0.21 em d2551149cdb949602f3cbcfdc0d29dd0f404c0d7, em pasta distinta para testes.

## Ainda falta
QA de batalha/vitória/salvar/reabrir desses quatro grunts, das batalhas da Route24, roteiro completo de MtMoon com Miguel/fósseis, outros eventos Rocket, Silph Co., S.S. Anne, puzzles, Elite Four, arte e áudio FireRed, PokéNav/Fly e multiplayer/Android; auditoria CI GBA legada separada.
