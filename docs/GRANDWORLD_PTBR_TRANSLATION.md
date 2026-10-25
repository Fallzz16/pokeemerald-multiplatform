# Pokémon Grand World GBA — plano e implementação de localização PT-BR

## Decisões do usuário (25/10/2026)

- **1A**: português brasileiro.
- **2A**: objetivo final de localização abrangente, incluindo histórias, menus, interface, mensagens de batalha e missões.
- **3A**: nomes de Pokémon e personagens permanecem originais.
- **4B**: nomes de golpes, habilidades e itens permanecem em inglês (mesmo com descrições e textos de interface traduzidos).
- **5A**: ROM exclusivamente em português, sem seleção de idioma em tempo real, preservando a ROM inglesa em sua branch.
- **6A**: diálogos naturais, similares à experiência de um jogo oficial em português.
- **7E**: priorização técnica: primeira etapa de interface, salvamento, Pokédex e abertura antes das campanhas regionais.

## Implementação desta branch

A branch parte exatamente de feature/grandworld-postm8-grass-only-20261024,
commit c5045b3bfadd96f77267775afc0ce5dbb95ff35d. Não altera main nem
mescla a PR #76.

A pipeline faz checkout de evilchinesefood/PKMN-World no commit fixo
15d3888b0d81322a04d3c71b0bce18948761ee44, aplica as integrações M8,
os 43 pilotos de famílias, seis perfis de herói, o orçamento lean e a regra
grass-only, nessa ordem. Só depois roda:

    python3 grandworld/tools/grandworld/translate_ptbr_stage1.py world --report ptbr-preflight.json
    python3 grandworld/tools/grandworld/translate_ptbr_stage1.py world --apply --report ptbr-report.json

Arquivos gerados/modificados apenas no checkout World efêmero:
- src/main_menu.c: menu, avisos de saves antigos/novos e carregamento.
- src/strings.c e src/battle_message.c: Pokédex, batalhas, bolsa, equipe, lojas, aprendizado de golpes,
  medicamentos, descrições de ações, caixas e outros textos da interface.
- data/text/save.inc e data/text/birch_speech.inc: salvamento e Hoenn.
- data/text/new_game_intro_frlg.inc: introdução de Kanto, Professor Oak,
  orientações de botões e apresentação das três regiões.
- data/text/obtain_item.inc, pc.inc, pc_transfer.inc, pkmn_center_nurse.inc
  e surf.inc: recompensas, PC, captura, atendimento e SURF.
- data/maps/RegionHub/scripts.inc: centro de viagens, regras de equipe/PC,
  Insígnias locais, placas, guias e acesso aos destinos regionais.
- data/text/move_relearner.inc, check_furniture.inc, day_care_frlg.inc:
  reaprendizado de golpes, interações e DAY CARE.
- data/text/ingame_trade_frlg.inc, shoal_cave.inc, lottery_corner.inc,
  questionnaire.inc, mauville_man.inc, abnormal_weather.inc, record_mix.inc:
  trocas, recompensas especiais, loteria, clima e NPCs de servicos.
- data/maps/LittlerootTown, OldaleTown, PalletTown_Frlg, NewBarkTown,
  CherrygroveCity, AzaleaTown, VioletCity, PewterCity_Frlg, RustboroCity,
  LittlerootTown_ProfessorBirchsLab e EverGrandeCity_ChampionsRoom:
  falas iniciais, placas, NPCs, missao DEVON/TEAM AQUA e Campeao.

Manifests de localização revisáveis e ancorados no inglês original:
- tools/grandworld/ptbr_extra_core.json: 205 entradas.
- tools/grandworld/ptbr_extra_events.json: 69 entradas.
- tools/grandworld/ptbr_extra_world.json: 78 entradas.
- tools/grandworld/ptbr_extra_battle.json: 142 entradas (mensagens de batalha).
- tools/grandworld/ptbr_extra_services2.json: 112 entradas (trocas, loteria, recompensas globais, hub e outros).
- tools/grandworld/ptbr_extra_regions2.json: 112 entradas (cidades iniciais, Johto/Kanto/Hoenn e Liga).
- tools/grandworld/ptbr_extra_story2.json: 134 entradas (Violet, Pewter, Rustboro e laboratorio de Birch).
- tools/grandworld/ptbr_extra_labs3.json: 114 entradas (Oak e Elm; Kanto e Johto).
- tools/grandworld/ptbr_extra_gyms3.json: 68 entradas (Brock, Falkner e Roxanne; lideres, NPCs e dicas).
- tools/grandworld/ptbr_extra_routes4.json: 79 entradas (Petalburg, Goldenrod, Route 101, Route 29).
- tools/grandworld/ptbr_extra_gyms4.json: 56 entradas (Misty e Brawly; lideres e NPCs).
- Dados anteriores incorporados em translate_ptbr_stage1.py: 98 entradas.

Total configurado: 1.267 entradas em 44 arquivos do checkout World.
A contagem não equivale a 1.267 diálogos exclusivos nem a porcentagem
de localização de todo o jogo; a meta continua ser 100%.

O adaptador exige correspondência exata com todos os símbolos do upstream, valida
caracteres presentes em charmap.txt e rejeita alterações em macros {PLAYER},
{STR_VAR_1}, {PAUSE ...}, etc. O pré-teste não altera arquivos. O patch completo
é calculado antes de escrever; origem modificada/ausente interrompe a execução.

## Limites — não declarar tradução completa

Esta etapa é um **primeiro lote testável** e intencionalmente preserva
muitas telas inglesas ainda não auditadas. O objetivo 100% continua aberto.

A pedido do usuário, TODOS os novos textos PT-BR são convertidos para
ASCII comum sem acentos nem cedilha (ex.: "Voce", "Nao", "Pocao").
A regra é aplicada em plain_ptbr antes de inserir qualquer texto no
checkout World, preservando nomes originais de espécies, golpes, habilidades,
personagens e itens fora do escopo. Se algum símbolo incompatível passar
pela normalização, a tradução falha e nenhum arquivo é alterado.
Não vamos gastar esforço criando novos glyphs de ã/õ/ç: **essa tarefa foi
explicitamente cancelada pelo usuário**.

Rótulos de menu extremamente estreitos e quebra de linha de diálogos ainda
exigem inspeção visual em emulador mGBA. Compilar só prova que a codificação
e os scripts foram aceitos.

Os IDs de espécies, golpes, habilidades, itens, jogos salvos, números
de mapas, Pokédex e diálogos dinâmicos não são alterados. Não se deve
modificar o cabeçalho de identidade/saves antes de testes explícitos.

## Próximos lotes

1. Testes visuais e mGBA com a ROM PT-BR para caixa de diálogo,
   caracteres e save/Continue; text boxes mais estreitas devem ter
   quebra apropriada sem romper eventos.
2. Inventário total dos textos C, ASM, tabelas JSON e textos em imagens;
   medir cobertura real por região e estado (translated/reviewed/pending).
3. Diálogos completos dos NPCs, rotas, ginásios, Ligas e campanhas de
   Hoenn, Kanto e Johto, protegendo comandos/scripts/flags.
4. Sistema de batalha inteiro e descrições de golpes/habilidades/itens
   em PT-BR, mas nomes dos golpes/habilidades/itens INTACTOS em inglês.
5. As 51 suites do jogo World passaram a ser obrigatorias no workflow PT-BR
   apos compilar e executar boot/title no mGBA. Ainda faltam regressões visuais
   manuais de texto, seis protagonistas, saves e homologação para release.

## Entrega e segurança

O workflow grandworld-ptbr-stage1.yml compila a ROM GBA real, valida
mapas/sprites/tabelas, checa orçamento EWRAM/IWRAM/ROM, roda boot/title e
51 suites World no mGBA vinculados ao hash da propria ROM PT-BR e guarda
relatorios, logs, inventario de pendencias e SHA256 do binario,
mas nao publica arquivos de jogo de terceiros em artifacts. A PR permanece draft; nenhum merge automático.
