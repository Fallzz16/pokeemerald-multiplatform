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
- src/main_menu.c — novo jogo/continuar/ajustes e rótulos do menu de carregamento.
- src/strings.c — interface, comandos de bolsa, textos de Pokédex, loja e avisos.
- data/text/save.inc — telas e alertas de salvamento, sem alterar slots de save.
- data/text/birch_speech.inc — introdução local com placeholders preservados.

O adaptador exige correspondência exata com todos os símbolos do upstream, valida
caracteres presentes em charmap.txt e rejeita alterações em macros {PLAYER},
{STR_VAR_1}, {PAUSE ...}, etc. O pré-teste não altera arquivos. O patch completo
é calculado antes de escrever; origem modificada/ausente interrompe a execução.

## Limites — não declarar tradução completa

Esta etapa é um **primeiro lote testável** e intencionalmente preserva
muitas telas inglesas ainda não auditadas. O objetivo 100% continua aberto.

A fonte latina atual não possui os glyphs ã/õ/Ã/Õ no charmap. Para evitar
texto ilegível ou bytes mapeados para símbolos japoneses, o primeiro lote
utiliza formulações PT-BR que não precisam deles. O próximo trabalho P0
é acrescentar os glyphs visuais nos PNGs/fontes latinas, validar seus tamanhos
e registrar o mapeamento de charmap sem colidir com símbolos existentes.

Rótulos de menu extremamente estreitos e quebra de linha de diálogos ainda
exigem inspeção visual em emulador mGBA. Compilar só prova que a codificação
e os scripts foram aceitos.

Os IDs de espécies, golpes, habilidades, itens, jogos salvos, números
de mapas, Pokédex e diálogos dinâmicos não são alterados. Não se deve
modificar o cabeçalho de identidade/saves antes de testes explícitos.

## Próximos lotes

1. Glyphs acentuados incluindo ã/õ, testes de largura, captura de tela em
   mGBA e QA de carga/save/Continue nas três regiões.
2. Inventário total dos textos C, ASM, tabelas JSON e textos em imagens.
   Manter um manifesto de strings com estado translated/reviewed/pending.
3. Centro de viagens, caixas de diálogos, tutoriais, nomes de funções de
   interface, sistema de batalha e descrições (nomes próprios em inglês).
4. Tramas e NPCs de Hoenn, Kanto e Johto, auditando eventos e placeholders.
5. Verificação de ortografia, comprimento em pixels, 51 testes mGBA,
   gameplay save/Continue com seis heróis e homologação de ROM PT-BR.

## Entrega e segurança

O workflow grandworld-ptbr-stage1.yml compila a ROM GBA real, valida
mapas/sprites/tabelas, checa orçamento EWRAM/IWRAM/ROM e guarda relatório,
log de compilação e SHA256 do binário, mas não publica arquivos de jogo de
terceiros em artifacts. A PR permanece draft; nenhum merge automático.
