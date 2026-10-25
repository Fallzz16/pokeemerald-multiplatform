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
- tools/grandworld/ptbr_extra_dewford5.json: 23 entradas (Dewford, travessias com Briney, pesca e sinalizacao).
- tools/grandworld/ptbr_extra_routes5.json: 17 entradas (Route 109, SLATEPORT, Briney e Route 106).
- tools/grandworld/ptbr_extra_route110_6.json: 43 entradas (MAY/BRENDAN, ciclismo, TEAM AQUA).
- tools/grandworld/ptbr_extra_route111_6.json: 30 entradas (familia WINSTRATE, MIRAGE TOWER).
- tools/grandworld/ptbr_extra_route112_6.json: 8 entradas (METEORITE, MT. CHIMNEY).
- tools/grandworld/ptbr_extra_hoenn_routes6.json: 50 entradas (ROUTES 102, 103, 104).
- tools/grandworld/ptbr_extra_johto_routes6.json: 82 entradas (ROUTES 30, 31, 32, JOHTO).
- tools/grandworld/ptbr_extra_hoenn_routes7.json: 15 entradas (ROUTES 113, 114, 115).
- tools/grandworld/ptbr_extra_petalburg_story7.json: 25 entradas manuais da campanha de Norman e Wally.
- tools/grandworld/ptbr_extra_petalburg_rooms7.json: 27 entradas manuais de salas, treinadores e revanche.
- Dados anteriores incorporados em translate_ptbr_stage1.py: 98 entradas.

Total configurado manualmente: 1.587 entradas em 60 arquivos do checkout World.

Novas entradas manuais nesta grande continuidade: 228. Todas usam manifestos
JSON revisaveis; nenhum nome de item, golpe ou habilidade foi renomeado.
A execucao posterior do GitHub Actions e obrigatoria antes de chamar a ROM
compilada/homologada.

Lote de continuidade de 25/10/2026: adicionadas 23 traducoes de Dewford e
integradas ao tradutor e a verificacao minima de CI. Compilacao e testes
deste novo commit devem ser confirmados pelo Actions, independentemente
dos resultados do commit anterior.
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

## Continuidade — segundo lote costeiro (25/10/2026)

Adicionadas 17 entradas de Route 109 e Route 106, totalizando 40 novas
entradas nesta continuidade desde as 1.267 anteriores. A falha Python
SyntaxError do workflow #40172851882 foi identificada e corrigida no teste
Dewford. Os commits mais recentes precisam da propria execucao Actions
para confirmar compilacao, emulacao, cobertura e orcamento. PR draft mantida.

## Gerador opcional de rascunhos de grande escala

A pipeline `grandworld-ptbr-bulk.yml` foi criada para tentar produzir pelo menos
5.000 **rascunhos assistidos por modelo de traducao local** sem reescrever a
versao inglesa. O gerador `generate_ptbr_bulk_candidates.py` rejeita texto
sem traducao real, scripts sem formato seguro, placeholders perdidos,
caracteres nao ASCII, expansao excessiva e ausencia de glyphs. O workflow
nao envia nenhum lote a branch se o preflight, os testes Python, a compilacao
real GBA e `make validate` nao passarem. O alvo e exclusivamente a branch
PT-BR desta PR draft. O gerador nao publica ROMs.

IMPORTANTE: qualquer arquivo `ptbr_auto_review_*.json`, caso venha a ser
produzido, e marcadamente **rascunho para revisao humana**, nao traducao
final certificada. Seus valores nao devem ser confundidos com texto revisado,
nem com gameplay homologado. Corrigir terminologia, fidelidade, largura das
caixas e progressao de todas as regioes continua obrigatorio para release.

## Progresso registrado — lote 5200 + revisao Petalburg (25/10/2026)

- PR #77 continua **draft**, sem merge e sem alteracoes no ramo ingles.
- Manual: **1587 entradas** = 1535 anteriores + 52 novas da historia/ginásio de
  Petalburg. Outras **24 entradas** do lote automatico em Petalburg foram
  reescritas manualmente em PT-BR natural; nao aumentam a contagem.
- Automatico: **5200 entradas** em 21 manifestos
  `tools/grandworld/ptbr_auto_review_001.json` a `021.json`.
  Foram integradas na propria PR no commit e3407cbe. Essas entradas
  continuam marcadas para revisao humana; nao sao texto final homologado.
- **Total configurado: 6787 de 14801 entradas estaticas inventariadas**,
  faltando 8014 entradas nesse escopo. Isso e ~45.85% apenas do inventario
  estatico conhecido, nao da localizacao integral do jogo.
- A compilacao de 6735 entradas mais antiga passou `make validate` no
  workflow #40178202749. A ROM com as 52 entradas adicionais e 24 revisoes
  ainda precisa de um NOVO GitHub Actions verde e de inspecao visual.
- Artefato de geracao inicial #12592517986 registra a proveniencia e os
  5200 textos. O gerador usou Argos en-pt 1.9; sua saida inclui portugues
  europeu e problemas editoriais. Nao usar como substituto de revisao PT-BR.
- O adaptador `adapt_ptbr_greedy_gifts_qa.py` preserva as verificacoes
  de exclusividade de iniciais Elm/Birch, agora com variantes traduzidas.
- Pendentes: revisao linguistica dos 5200 rascunhos, caixas de texto e
  todos os textos fora da auditoria (C dinamico, graficos etc.), testes de
  save/continue e homologacao manual em Hoenn, Kanto e Johto.


## Revisao humana de rascunhos — ginásios (25/10/2026)

- Alem das 1.587 entradas originalmente manuais, foram revistos individualmente
  **120 textos** que ja faziam parte das 5.200 traducoes automaticas.
  Isso nao aumenta a quantidade total de entradas, que continua **6.787**.
- 24 falas no GYM de Petalburg (Norman e treinadores); 18 em Azalea
  (Bugsy); 18 em Goldenrod (Whitney); 20 em Ecruteak (Morty); 21 em
  Mahogany (Pryce); 19 em Blackthorn (Clair).
- Foram corrigidos portugues europeu, falas pouco naturais e termos tecnicos.
  Em Azalea, TM09 mantem explicitamente o nome do golpe **BULLET SEED**.
- O registro `tools/grandworld/ptbr_reviewed_auto7.json` diferencia textos
  que receberam revisao linguistica humana daqueles que ainda sao rascunhos.
  Nenhum recebeu automaticamente selo de gameplay homologado ou QA visual.
- Testes verificam a presenca dos 120 simbolos revisados e protegem a
  grafia de BULLET SEED; a PR permanece draft, sem merge.
