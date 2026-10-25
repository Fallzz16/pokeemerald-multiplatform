# Grand World Native — P2 (ligação da engine real)

**Última implementação:** 2026-10-25. Trabalho na branch experimental
`experiment/grandworld-native-p0-p5-plugins-20261025`, PR #78.
Não realizar merge na M8 estável nem na tradução PT-BR sem testes.

## O que está realmente pronto

- O `AgbMain()` e o frame real da World foram expostos para a plataforma:
  `GwWorldFrame()` / `GwWorldVBlank()`, preservando o loop GBA fora de
  `GW_WORLD_NATIVE`.
- `gw_world_desktop.c` chama `AgbMain`, frame da World, `DrawFrame`, VBlank
  e apresenta os pixels pelo backend SDL2; é **código-fonte, não jogo compilado**.
- Os shims BIOS/DMA/memória e áudio têm smoke tests reais e testes ASan/UBSan.
- `engine_probe.py` recompila os arquivos `src/*.c` reais usando o
  `cpp | preproc` da World, charmap e assets originais, incluindo PT-BR/M8.
- `data_asm_probe.py` compila dados de `data/*.s` originais com adaptação
  de diretivas ARM `.align/.word` à semântica i386 `.p2align/.4byte`.
- `engine_link_probe.py` produz **somente um objeto relocável** para
  diagnosticar símbolos faltantes. Ele não é executável.
- `real_data_link_probe.py` verifica a resolução por dados reais, sem
  inventar rótulos, sprites, ROMs ou funções.

## Evidências de compilação já medidas

- Diagnóstico C da World/M8: **402 de 405** fontes C compilaram no run
  que produziu `GrandWorld_P2_40202030541_C_ASM_Diagnostics.zip`.
  Os erros então restantes eram `m4a.c`, `multiboot.c` e `random.c`.
  Adaptadores portáveis específicos já foram escritos; validar o status final
  no CI após a geração da ROM de referência.
- No mesmo diagnóstico, **13 de 14** unidades de `data/*.s` compilaram.
  `event_scripts.s` falhou em expressões de script da Game Corner Celadon e
  diretivas de alinhamento de Cherrygrove. O adaptador de assembly foi
  atualizado, mas isso exige confirmação na execução final.
- O objeto relocável C de 402 unidades tinha **3.876 símbolos indefinidos**.
  Esse número inclui referências de dados, código e serviços que ainda
  precisavam entrar na linkagem. Não equivale a 3.876 bugs.
- Layouts medidos de `SaveBlock1/2/3` igualados entre GBA ARM APCS e GCC32,
  sem desativar `STATIC_ASSERT`. Salvamento end-to-end segue pendente.

### Atualização medida na CI 40203936946

Na [execução 40203936946](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40203936946):
- **405/405** módulos C da M8/World compilaram para x86-32 com os adaptadores
  ARM nativos; os objetos tiveram link relocável real.
- **3.815** símbolos permaneceram sem definição no objeto C relocável.
- A conversão prematura do assembly causou regressão: apenas **4/14**
  arquivos principais de dados compilaram; só 2 dependências foram
  resolvidas ao juntar os dados naquela execução.
- A cadeia foi reestruturada em `data_asm_staging.py`: a World original
  agora preprocessa textos e roteiros intactos primeiro, e a adaptação GAS
  acontece depois, apenas para o assembler hospedeiro.
- O status de assembly **após** essa correção exige CI nova; não apresentar
  14/14 como confirmado.
- `final_link_probe.py` irá registrar a falha de linkagem final real,
  separando símbolos indefinidos, duplicados e cobertura C/ASM, sem
  inventar recursos ou declarar gameplay testado.

## O que esta continuação acrescentou

1. Corrigiu as strings de quebra de linha de um teste de assembly real que
   interrompia o CI antes do build da engine.
2. Criou `final_link_probe.py`: tenta **linkar o executável completo** com
   C original, assembly original, componentes de plataforma e entrada SDL2.
   Não usa `--unresolved-symbols=ignore-all`, funções vazias ou conteúdo falso.
3. Acrescentou uma etapa CI para compilar explicitamente os arquivos objetos
   de BIOS, DMA, áudio, renderização, host SDL2 e entrada da World com a
   mesma ABI i386; o relatório reúne símbolos indefinidos e duplicados.
4. Relacionou resultados do linker com a cobertura real de compilação C
   (`compiled/requested`) e ASM (`native_objects/original_source_files`),
   evitando declarar engine completa por apenas existir um ELF.
5. Eliminou arquivos `.o` anteriores quando uma compilação C ou ASM falha;
   testes impedem linkagem acidental de código desatualizado.
6. Acrescentou testes de falhas do linker, completude de fontes e inexistência
   de falsos relatórios de boot.

## Critérios para concluir P2

- [ ] Todos os módulos necessários C/ASM reais geram objetos de host.
- [ ] O linker do executável World/M8 + SDL2 não encontra símbolos externos
      não resolvidos nem definições duplicadas.
- [ ] O executável inicializa `AgbMain` e roda o frame real sem crash.
- [ ] Tela gerada pela engine real aparece em SDL2 com teclado/controle.
- [ ] O projeto GBA de referência continua recompilando e validando.
- [ ] O engine mantém saves sem corrupção e a mesma definição de regiões.

**Estado:** P2 em andamento. Um Style Lab, um objeto relocável ou um
`gw_world_desktop.o` compilado nunca devem ser anunciados como jogo jogável.

## Próximas ações práticas

Ler o artefato `native-m8-final-link-attempt.json` do job
`native-source-lab` em `.github/workflows/grandworld-native-experimental.yml`.
Atacar os símbolos indefinidos agrupados por origem real e compilar seus
arquivos C/ASM originais. Reexecutar os testes de BIOS/DMA/save em cada avanço
e somente então validar a inicialização da World. Não criar stubs para
simular progresso ou substituir recursos protegidos.
