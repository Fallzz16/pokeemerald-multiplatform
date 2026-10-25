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
- Hipótese **sob teste**, e não correção de produção: cada
  `struct BattleDomeTrainer` deveria ocupar 4 bytes, enquanto o
  compilador nativo pode colocá-lo em 2 bytes. Existem 16 registros:
  `16 × (4 - 2) = 32` bytes.
- O restante de 4 bytes exige medir `struct Time` e os campos anteriores.
- `abi_probe.py` experimenta `aligned(4)` **apenas em um header temporário**.
  Os headers reais e os saves continuam intactos.

Nunca retirar o `STATIC_ASSERT` para "resolver" P1. Conferir offsets e
semântica dos bitfields entre compiladores antes de qualquer serialização.

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
- [ ] ABI nativo comprovadamente compatível campo a campo.
- [ ] Linker gera World/M8 completo como nativo.
- [ ] Bootstrap real World em SDL2.
- [ ] Movimento nas 3 regiões + saves verificados.
- [ ] Batalhas, áudio e seguidores reais validados.
- [ ] Jogo Windows distribuível (P5).
- [ ] Android APK.

**Nunca chamar o ZIP de Style Lab de “Grand World jogável”.**
