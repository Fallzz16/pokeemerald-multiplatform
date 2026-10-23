# Kanto V0.25 — recuperação da compilação GBA

Branch: `feature/kanto-v25-gba-recovery-modern-legacy`.
Base imutável: V0.24 `f36abb8ba3fa7234b6a9a65fa7c9ce142ca6d5ea`.
FireRed fixo: `ce6406d8c2eaf46d543c8a2606de0c3cb1951982`.

## Diagnóstico
- O CI antigo compilava agbcc primeiro (`MODERN=0`, `COMPARE=1`), interrompendo o job antes de compilar no ARM GCC moderno. A igualdade de checksum com a ROM original não é critério válido para uma ROM modificada.
- `include/gba/macro.h` tinha `#if defined MODERN` na macro DmaSet. `MODERN=0` continua definido, ativando incorretamente as verificações C11 `_Static_assert`, `_Alignof` e `__builtin_choose_expr`. Corrigido para `#if defined(MODERN) && MODERN && !defined(PORTABLE)`.
- `include/sound_mixer.h` tinha atributo de alinhamento antes de `float outBuffer`, sintaxe rejeitada pelo agbcc. A declaração agora usa atributo somente em MODERN=1; a declaração legada mantém o mesmo tipo, dimensões e posição lógica. Ainda é necessário validar alinhamento real no ARM.

## Implementações
1. Verificações extras de headers em `tests/test_gba_syscall_guards.py`, incluindo expansão de DMA em dois modos.
2. Workflow `.github/workflows/build.yml` com jobs independentes:
   - `gba-modern` **obrigatório**: instalações de toolchain ARM GCC e bibliotecas, importação completa de Kanto, `make MODERN=1 COMPARE=0 all`, validação de ROM até 32 MiB, SHA256 e upload dos binários/log.
   - `gba-agbcc-legacy` **diagnóstico explícito, não bloqueante**: compila `MODERN=0 COMPARE=0` com compilador agbcc, registra o próximo erro real; nunca exige hash igual ao Emerald original.
3. Ambos os jobs materializam os mapas e treinadores Kanto antes da compilação; não substituem flags nem IDs, não editam saves reais.
4. Workflow Windows de V0.24 continua como regressão na branch V0.25.

## Reproduzir na máquina do desenvolvedor
Com Linux, ARM GCC, newlib, libpng e Pillow, e pasta `firered-source` no commit acima:

```bash
python -m unittest discover -s tests -p test_gba_syscall_guards.py -v
python tools/kanto/import_exteriors.py --firered firered-source --emerald . --report kanto-gba-materialization.json
make -j2 MODERN=1 COMPARE=0 all
# diagnóstico opcional após instalar agbcc:
make -j2 MODERN=0 COMPARE=0 all
```

Saída moderna pretendida: `pokeemerald_modern.gba`; logs e artefatos publicados nas ações do GitHub. **Build aprovado não confirma boot ou gameplay em emulador.**

## Critérios de QA pendentes
- Inspecionar o CI no SHA exato; se o compilador moderno falhar, corrigir os erros de linker/includes até obter ROM ou documentar bloqueio verificável.
- Rodar mGBA com ROM real e save de teste isolado: boot, novo jogo, ida Hoenn–Kanto, mapas críticos, batalhas e saves/flags após fechar/reabrir.
- Verificar áudio e offsets/alinhamento do mixer na toolchain ARM; checar limite de 32 MiB e SRAM disponível.
- Corrigir o restante do agbcc somente quando apropriado, sem forçar código moderno em compilador incompatível.
- Manter QA de dois PCs, Android e compatibilidade de saves como trilhas separadas.

## Referências externas
- pret/pokeemerald: https://github.com/pret/pokeemerald/blob/master/INSTALL.md
- pokeemerald-expansion (depreciação agbcc): https://rh-hideout.github.io/pokeemerald-expansion/changelogs/1.9.x/1.9.0.html

## Reversão segura
Retornar à V0.24 `f36abb8ba3fa7234b6a9a65fa7c9ce142ca6d5ea`; nunca substituir saves originais. Alterações se restringem a guards de compilação, declaração de alinhamento, testes, CI e documentação.
