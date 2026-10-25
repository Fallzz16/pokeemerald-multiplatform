# Pokémon Grand World Native — auditoria corretiva e preparação P1

**Escopo:** branch `experiment/grandworld-native-p0-p5-plugins-20261025`,
PR #78. Não fazer merge automático.
**Estado:** núcleo de jogo World/M8 **ainda não possui executável nativo jogável**.
O Style Lab é uma prova de plataforma e recursos, não a engine World.

## Fonte preservada

- World fixa em `15d3888b0d81322a04d3c71b0bce18948761ee44`.
- Composição existente M8, modo de encontros na grama, PT-BR e QA.
- Original `main`, branch de tradução e saves `.sav` não foram modificados.
- GBA de referência recompilado e validado no CI
  [execução 40187063753](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40187063753).
- O GBA permanece prova de regressão; não é o novo aplicativo.

## Correções da varredura

### 1. Pacotes ZIP / instalação

`modpacks.py`, `pack_manager.py`, `asset_catalog.py`:

- Rejeição de nomes que poderiam quebrar ou injetar linhas no catálogo TSV
  do leitor C (caminhos somente ASCII minúsculo `a-z0-9._-/`).
- Rejeição de entradas de diretório inválidas, symlinks ZIP, duplicatas,
  versões sem componentes válidos, caminhos e IDs lógicos indevidos.
- `classic` é palavra reservada da interface nativa e não pode ser ID de pack.
- Instalação copia o ZIP para uma área privada temporária sob a pasta de mods,
  valida esse snapshot e somente então extrai. Erros deixam o pack anterior intacto.
- O limite de **2.048 assets habilitados** é igual ao `GW_STYLE_MAX_ASSETS`
  do leitor C. Tentar excedê-lo falha e restaura o índice anterior.
- Manifestos JSON corrompidos não derrubam a listagem do gerenciador gráfico.
- Não se executam scripts, DLLs nem plugins arbitrários. Hash SHA-256 verifica
  integridade, não autorização ou autenticidade do autor.

### 2. Interface C / SDL2

`gw_theme_lab.c`, `gw_style_index.c`:

- Pressionar **F5** carrega um novo catálogo + preferências em estado provisório.
- Se o índice não puder ser lido, ou uma imagem estiver corrompida, mantém
  os recursos já decodificados e a configuração de estilo anterior.
- Arquivo de índice não existente é válido (modo clássico), mas arquivo
  existente que não possa ser aberto não é tratado como modo clássico.
- Configurações persistidas permanecem em `mods/style-settings.ini` e não
  modificam os SaveBlocks da World.

### 3. Testes acrescentados

`tests/test_audit_regressions.py`:

- Diretório `../` dentro de ZIP.
- Diretório de tipo symlink dentro de ZIP.
- Versões e IDs inválidos.
- Filename com maiúscula, quebra de linha, tabulação, espaços e `..`.
- Falha no catálogo durante instalação ou ativação com rollback.
- Pack ID reservado e metadados malformados.

Conjuntos já existentes: unidades Python, teste SDL2 Linux, teste nativo
Windows, C smoke de escolha de estilos, gerenciador Windows. Status exato
de cada execução deve ser verificado na aba **Actions** do PR.

## Bloqueador prioritário para o jogo REAL: save ABI

A árvore World contém `STATIC_ASSERT(sizeof(struct SaveBlock2)==0xF2C)`.

Medições GCC 32 bits de referência (antes do experimento de alinhamento):

- Size GBA esperado: **3884 bytes**.
- Size nativo GCC: **3848 bytes**; diferença de **36 bytes**.
- `playerApprentice` e campos seguintes aparecem **4 bytes antes** do
  offset documentado.
- `BattleFrontier.domeTrainers` começa no offset esperado, mas
  `domeMonIds` e campos posteriores aparecem **32 bytes antes**.
- **Confirmado pelo compilador 32-bit:** cada `struct BattleDomeTrainer`
  ocupa 2 bytes nativamente e precisa de 4; 16 registros explicam
  `16 × (4 - 2) = 32` bytes.
- **Confirmado:** cada `struct Time` mede 6 bytes nativos e precisa de 8.
  As duas instâncias explicam os outros 4 bytes.
- Com os dois tipos alinhados em 4 bytes, o compilador mediu **3884 bytes**,
  e **todos os offsets auditados coincidiram** (perfil `gcc32-time-dome-aligned-4`).
  Evidência: [CI 40189037378](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40189037378).
- `abi_probe.py` faz a comparação em headers temporários. O adaptador
  `save_abi_overlay.py` consegue aplicar a alteração **somente para PORTABLE**
  em uma árvore descartável **após** a referência GBA. Não foi feita migração
  de saves e a semântica dos bitfields ainda exige testes específicos.

Nunca retirar o `STATIC_ASSERT` para "resolver" P1. Conferir offsets e
semântica dos bitfields entre compiladores antes de qualquer serialização.

## Resultados adicionais verificados — P1 (25/10/2026)

- [CI 40189037378](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40189037378):
  GCC 32 bits com `Time` e `BattleDomeTrainer` alinhados a 4 bytes
  reproduziu **3884 bytes e zero diferenças nos offsets auditados**.
- [CI 40189712888](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40189712888):
  comparação de seções binárias ARM APCS e GCC32 confirmou bytes idênticos
  para **24 bytes de amostras de Time** e **20 bytes de amostras de bitfields
  BattleDomeTrainer**. Isso não é um teste de save completo.
- [CI 40189300572](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40189300572):
  `save_abi_overlay.py` foi aplicado com sucesso **depois** da compilação e
  validação GBA, somente na árvore descartável da World.
  Após a auditoria de 25/10, concluímos uma camada de compatibilidade
  *isolada* para os quatro componentes. O estado anterior, abaixo, foi
  substituído pelas evidências mais recentes:

- [CI 40191964730](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40191964730):
  quatro arquivos passaram em GCC 32-bit com `-Werror=implicit-function-declaration`,
  e o teste C executável validou BIOS (incluindo RLE), DMA
  imediato/VBlank/repetição/fonte fixa, buffers de hardware e limites de áudio.
- [CI 40192254680](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40192254680):
  `gba_easy_draw.c` também gerou objeto nativo `.o`; o teste de runtime
  com **AddressSanitizer e UndefinedBehaviorSanitizer** passou.
- `dma_api_overlay.py` conserva o caminho GBA e redireciona somente
  `GW_WORLD_NATIVE` aos registros emulados e à função de transferência
  `GwNativeDmaSet`. Os `STATIC_ASSERT` do sistema de saves foram mantidos.

| Módulo | Validação isolada em World 32-bit | Observação |
|---|---|---|
| `bios.c` | COMPILA E EXECUTA TESTES | Correção real de avanço de ponteiro RLE; cópia e preenchimento |
| `dma.c` | COMPILA E EXECUTA TESTES | DMA 16/32-bit, NOW, VBlank, reload, canal inválido |
| `gba_easy_draw.c` | COMPILA ARQUIVO OBJETO | A tela real da World ainda não está conectada |
| `cgb_audio.c` | COMPILA E EXECUTA TESTES | RAM de ondas e limites de buffer; música do jogo ainda não validada |

**Escopo da conclusão:** BIOS/DMA/memória/áudio da plataforma sob testes
isolados. Ainda **não** existe um executável com toda a World/M8 ligada ao
SDL2, nem teste end-to-end de saves. O próximo passo é integrar o ciclo
principal real e testar os recursos dentro da engine, não apenas em harnesses.

## P2 — progresso real da compilação World/M8 (25/10/2026)

**Última evidência concluída e inspecionada:** [CI 40202030541](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40202030541).
A composição M8 + PT-BR e a referência GBA são verificadas antes das
adaptações `GW_WORLD_NATIVE`. Não houve merge na base estável.

- **402/405** arquivos `src/*.c` compilaram para objetos GCC/i386 com
  textos e gráficos reais, sem substitutos. Os três pendentes eram
  `m4a.c`, `random.c` e `multiboot.c`, todos contendo instruções ARM
  não aceitas pelo x86 GAS. `arm_runtime_overlay.py` agora isola versões
  nativas dessas rotinas na árvore temporária, mantendo o caminho ARM intacto.
  Resultado pós-correção: **ainda requer confirmação em novo CI**.
- **13/14** arquivos `data/*.s` foram montados em objetos ELF32 reais.
  `data/event_scripts.s` falhava com 3 operandos de scripts Celadon e 2
  diretivas de alinhamento GBA. `gba_data_asm_overlay.py` converte somente
  sintaxe específica do assembler, depois da compilação GBA.
  Resultado pós-correção: **ainda requer confirmação em novo CI**.
- A ligação parcial dos 402 objetos C existentes passou, com **3.876
  símbolos externos não resolvidos**. Isso é esperado enquanto faltarem
  scripts/recursos ASM e os serviços da plataforma; **não é um .exe**.
- `real_data_link_probe.py` mede quais símbolos são efetivamente
  resolvidos pela adição de dados originais. `symbol_source_audit.py` aponta
  prováveis arquivos donos de labels não resolvidos; os dois preservam evidências
  em JSON e não fabricam definições.
- O CI agora **falha explicitamente** se faltar qualquer `src/*.c`, se um
  arquivo `data/*.s` não montar, ou se a ligação relocável C+dados falhar.
  Uma indicação verde anterior a esses gates não comprova completude.

**Próxima barreira real:** após uma auditoria 405/405 e 14/14,
verificar símbolos do executável completo, rotinas ASM do GBA que ainda
precisam de backends nativos, endereços de memória, áudio/inputs e primeiros
frames reais. Nenhuma tela/título/screenshot ou save real foi validado aqui.

## P2 — checkpoint de compilação completa C, 25/10/2026

**Evidência:** [Actions 40210875980](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40210875980),
job `native-source-lab`, com JSONs anexados (`native-engine-m8-survey.json`,
`native-engine-m8-survey-link.json`, `native-m8-data-asm.json`).

- A composição World + M8 + PT-BR e **compilação/validação GBA de
  referência passaram**, ANTES de overlays nativos, em checkout descartável.
- **405/405 fontes C originais foram compiladas** como objetos GCC/i386,
  agora incluindo `m4a.c`, `multiboot.c` e `random.c`. Isto supera
  a antiga referência 402/405, sem reescrever a engine.
- A **ligação relocável apenas dos objetos C** passou com **3.815
  símbolos externos ainda não resolvidos**. Não é um programa executável.
  A maioria desses símbolos refere-se a dados/scripts originais ainda
  não incluídos nessa ligação, portanto esse número NÃO representa uma
  contagem definitiva de rotinas nativas faltantes.
- **13/14 fontes `data/*.s`** montaram com GAS/i386. A única falha
  continua em `data/event_scripts.s`: as três invocações de
  `goto_if_ge` em Celadon City (linhas 137, 197 e 224 do
  `scripts.inc`) geram `too many positional arguments`.
  Avisos de `copyvar` aparecem no log, mas não são os erros fatais.
- O scan do overlay contabilizou **3 transformações Celadon**, porém o
  preprocessor original já havia preparado um snapshot do assembler
  antes das alterações nas fontes `.inc`. A correção subsequente
  [46e81c01](https://github.com/Fallzz16/pokeemerald-multiplatform/commit/46e81c01af8541a071888b8987102d9231fce4bd)
  aplica a transformação restrita também ao stream genuíno preparado;
  [e149630b](https://github.com/Fallzz16/pokeemerald-multiplatform/commit/e149630b28642da05bf1a883ef3a89a1920505c5)
  adiciona teste de regressão que exige gerar objeto ELF32 real com as
  três chamadas. **Essas alterações ainda dependem de novo CI completo.**
- A falha anterior de fixture ARM com `\\n` literais foi corrigida em
  [46c68ad3](https://github.com/Fallzz16/pokeemerald-multiplatform/commit/46c68ad3efa713bbb0b5360afe4a6728e7baa310);
  os testes de backend passaram em 40210875980.
- A verificação rápida de objetos ELF32 foi separada da instalação
  dispendiosa de SDL2-dev:i386 em
  [20ab85d4](https://github.com/Fallzz16/pokeemerald-multiplatform/commit/20ab85d4b761417946c3ccbf1bab28033d951145).
  A linkagem executável ainda requer as bibliotecas SDL2 de 32 bits
  e continua na etapa `native-source-lab`.

**Próximo bloqueio técnico verificável:** confirmar 14/14 dados reais,
ligar os 405 objetos C mais os 14 objetos ASM em modo relocável, medir
novamente `nm -u`, e só então tentar a linkagem ELF com a camada SDL2
sem símbolos simulados. **Nenhum executável World/M8 que inicialize,
renderize ou salve gameplay foi demonstrado neste checkpoint.**

## Arquitetura concreta recomendada

Manter a World/M8 integrada como **fonte do jogo**, e reaproveitar a camada
de plataforma do port SDL2 existente; NÃO copiar a lógica da M8 para o
Emerald nativo antigo.

Ordem de implementação:

1. **P1a — memória e ABI.** Confirmar tamanho/offset/bitfields de SaveBlocks,
   alocar VRAM, OAM, paletas e registradores virtualizados, definir API
   `gw_native_platform.h` sem contaminar compilação GBA.
2. **P1b — BIOS, DMA e interrupções.** Resolver conflitos de macros `CpuSet`,
   `CpuFastSet`, `DmaSet` e constantes DMA. Compilar os arquivos da engine
   World com esses shims. O SDL2 host atual **não** é essa integração.
3. **P1c — construir/ligar World.** Um único executável com `main` nativo,
   ciclo de jogo World, logs e tela SDL2. Só marcar P1 quando o linker passar.
4. **P2 — bootstrap real.** Título/menus no Windows com pixels gerados pela
   World (não pelo Style Lab), screenshots e controles.
5. **P3 — conteúdo e saves.** Validar Região Hub, Kanto, Johto, Hoenn, save/
   reload e cópia de segurança. Sem alteração silenciosa de formato.
6. **P4 — batalhas/áudio/seguidores.** QA funcional, diferenças visuais e
   oito orientações do follower opcionais para recursos externos.
7. **P5 — distribuição Windows.** Entregar ZIP `.exe` + DLLs apenas após
   provar P1–P4. **Android ARM64** somente depois, com auditoria de ponteiros.

## Interface futura de packs no jogo

Os pacotes atuais usam `manifest.json`, catálogos por ID lógico
(`menus/background`, `sprites/follower`, `sprites/follower/ne`, etc.),
índice `runtime-assets.tsv` e preferências `style-settings.ini`.
O próximo passo é criar um `ResourceResolver` C com versão e fallback
para assets internos no ciclo de desenho real da World.

Os dados de menus/seguidores são **cosméticos**. Alterar saves para salvar
opções visuais não é necessário e deve ser evitado.

## Critérios de aceite

- [x] P0 base GBA reproduzida e validada em execução anterior.
- [x] Style Lab SDL2 e pack manager funcionais como protótipos.
- [x] Correções de ZIP + regressões automáticas implementadas.
- [x] Layout de `SaveBlock2`: tamanho e offsets, mais amostras de bitfields
      conferidos entre GBA ARM APCS e GCC32 (não é save end-to-end).
- [x] Componentes P1 de BIOS/DMA/memória/áudio compilados em harness World32.
- [x] Testes de transferência/decodificação e ASan/UBSan nos caminhos exercitados.
- [ ] Semântica completa dos saves e efeitos de hardware conferida em gameplay.
- [ ] Linker gera World/M8 completo como nativo.
- [ ] Bootstrap real World em SDL2.
- [ ] Movimento nas 3 regiões + saves verificados.
- [ ] Batalhas, áudio e seguidores reais validados.
- [ ] Jogo Windows distribuível (P5).
- [ ] Android APK.

**Nunca chamar o ZIP de Style Lab de “Grand World jogável”.**
