# Emerald Hybrid LAN v0.8 — Fundação M0/M1 (núcleos separados)

**Status: código C99 independente implementado e testado no Linux local. Não existe jogo v0.8, launcher ou servidor dedicado funcional nesta entrega.** O gameplay comprovado anteriormente segue na branch `feature/lan-v0721-viewport-culling`.

## Arquivos implementados

| Arquivo | Objetivo |
|---|---|
| `src/lnet/lnet_session_v1.h` e `.c` | Formato de mensagem EHL8, cabeçalho 28 bytes, payload <=4096, versões e tipos definidos, serialização big-endian e decodificação incremental segura |
| `src/profile/save_profiles.h` e `.c` | Importar um .sav sem modificá-lo; criar perfil vazio; bloqueio de escrita concorrente; backups, restauração e retenção configurável |
| `tests/test_lnet_session_v1.c` | 192 roundtrips de payload/tamanho/fragmentação, cabeçalhos inválidos, frames concatenados e limites |
| `tests/test_save_profiles.c` | Importação bit a bit, formatos 128 KiB e +16 bytes, IDs sem traversal, bloqueio duplo, backups, restauração e recuperação de arquivo corrompido |
| `scripts/verify_lan_v080_foundation.sh` | Script reproduzível que compila e executa os testes |
| `tools/emerald_profilectl.c` | Ferramenta nativa de **desenvolvedor** com comandos `validate`, `new`, `import`, `backup`, `restore`, `prune`; não é launcher nem modifica saves fora do perfil selecionado |
| `.github/workflows/test-lan-v080-foundation.yml` | Linux normal/sanitizers e cross-compilação Windows x86 |

As rotinas agora **revalidam o destino após a cópia** de importação e backup; a criação de novo perfil tenta limpar diretórios parciais em caso de falha. O formato ainda recebe validação apenas estrutural (sem checksums completos). O teste de save **gera arquivo sintético temporário de cabeçalhos**, que não é jogável. **Nunca distribuí-lo como save real**. Os testes não leem, não criam nem alteram saves do usuário.

## Testar

```bash
bash scripts/verify_lan_v080_foundation.sh
SANITIZE=1 bash scripts/verify_lan_v080_foundation.sh
```

Resultados verificados no Linux local e em GitHub Actions (execução deste incremento deve ser consultada pelo SHA):
- 192 testes de roundtrip, mais rejeição de pacotes inválidos: PASS
- Importações intactas, locks, backup/restore/retention, corrupção simulada: PASS
- CLI de desenvolvedor (novo perfil e recusa de backup do flash apagado, travessia de diretório): PASS
- Compilação cruzada Windows x86 das bibliotecas e CLI: PASS no workflow do incremento (confirmar em Actions no HEAD)

**O status final de CI dependerá do SHA do último commit.** Verificar workflow antes de declarar Windows aprovado.

## Limites de segurança e compatibilidade conhecidos

1. O protocolo **não possui socket, servidor, lobby ou autenticador ainda**. Não misturá-lo ao stream TCP legado do Cable Club (45680) nem ao stream presença legado (45681).
2. A validação de .sav é **ESTRUTURAL, NÃO completa**: tamanho 131072/131088 bytes, IDs 0..13, assinatura `0x08012025` e contador de slot. Não verifica checksums individuais nem coerência de mapas, Pokémon ou história. Não alegar reparo de saves.
3. Operações de backup/restore requerem lock do perfil **e o jogo parado de escrever**. O SDL2 atual ainda não usa este lock nem seleciona caminhos por perfil.
4. `sp_import` exige um diretório root criado previamente e ID de perfil fornecido pelo chamador. Faltam UUID aleatório, manifestos, aliases/nomes, seleção app-data/portátil, backup/exportação ZIP, Android SAF e metadados.
5. O lock em POSIX é via `flock`; Windows usa handle exclusivo. Locks protegem **somente consumidores que cooperam** com o sistema. Um editor externo ou o executável antigo podem gravar no mesmo arquivo.
6. Cópia usa arquivo `.partial`, `fflush/fsync` e rename/MoveFileEx; a durabilidade real diante de perda de energia (incluindo fsync de diretórios) ainda não foi testada. Caminhos Windows Unicode e limites de comprimento precisam de trabalho adicional.
7. `sp_create_empty` escreve flash apagada 0xFF, para que **o jogo** inicie e grave normalmente; não é um save Emerald completo pré-fabricado.
8. As respostas do usuário **1–100** estão registradas em `docs/LAN_V080_ARCHITECTURE.md`; primeira versão funcional #100A só pode ser declarada após servidor dedicado, lobby, saves próprios e duas instâncias reais em jogo. O limite final de quatro jogadores é posterior.
9. Sem alteração em `src/platform/sdl2.c`, Quest UI, PokéNav, áudio, scripts, movimentos, SIO, ROM/GBA ou saves originais nesta entrega.

## Próximo incremento — em branch distinta

1. Completar inspeção real de checksums do formato Emerald e testar importação com arquivos reais do usuário **somente após consentimento/backup**; também evitar alterações silenciosas de saves.
2. Criar ID persistente de perfil, metadados, localização app-data/portátil, backup de migração e lock acoplado ao ciclo completo do jogo.
3. Integrar `--save-path` com o SDL2 atual sem quebrar modo offline; só depois ativar opção de múltiplos perfis.
4. Implementar socket real para SessionServer com lobby 2 clientes, PIN e timeout; UI moderna só quando APIs forem confiáveis.
5. Criar matriz Windows/Android real e revalidar batalhas/trocas antigas, save/reload, FPS, desconexão e entrada tardia antes de anunciar v0.8 funcional.

## Rollback e continuidade

- Branch desta fundação: `feature/lan-v080-m0-m1-foundation`, [PR #6 experimental](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/6) contra `feature/lan-v080-architecture-spec`.
- Baseline de gameplay validado pelo usuário: `feature/lan-v0721-viewport-culling`, commit `a87e2c49e453db32def5e71ba2a2e696a911d504`.
- **Nenhum código pré-existente foi alterado:** basta não mesclar a branch para manter o jogo idêntico.
- `AI_README.md` é documento obrigatório de transferência entre IAs, com registro do que se implementou e do que ainda não foi.


## Experimental opt-in selected save in native SDL2 (M1 bridge)

The existing game can be started, *after using a separate trusted profile-management tool to create/import a profile directory*, with:

```text
pokeemerald.exe --profile-root="C:\\EmeraldProfiles" --profile-id=Player_A
```

Example expected folder: `C:\EmeraldProfiles\Player_A\pokeemerald.sav`. The root directory and profile must **already exist**; no migration or import is performed by launching the game.

- Requires **both** arguments; an invalid/missing/busy profile returns a nonzero exit instead of falling back to the default save.
- The `.profile.lock` OS lock is held for the game's lifetime (when a managed profile was selected). Other cooperating instances are denied until it closes.
- Both the flash image loader and `Platform_ReadFlash` now refer to `sActiveSavePath`. Legacy startup with no profile switches continues using `pokeemerald.sav`.
- On Android, the same native code can accept profile arguments, but the existing launcher does **not yet offer profile selection or pass these arguments**. Default Android private save storage remains unchanged.
- **No auto-backups happen during game saving yet**; backup/restore remain independent offline operations in `sp_backup/sp_restore`. This is intentionally NOT called inside flash I/O or Cable Club.
- Existing UI, battle, multiplayer, Quest UI and ROM rules were not modified. This change only selects a file for save/flash operations.

### Verification of the bridge

- GitHub Actions `test-lan-v080-foundation.yml` runs C99 unit tests and Windows x86 cross-compilation for the standalone modules. Added source assertions check both startup arguments and consistent selected file usage.
- Full native Windows x86 and Android candidate builds should be run on the exact commit SHA and log their conclusions separately. These builds do **not** prove actual multi-profile gameplay.
- Next runtime QA: create 2 profiles from two **unaltered real compatible .sav files**, launch two game processes with separate selected profile flags, load/save/relaunch, compare checksums and isolated content and test duplicate locks, missing/corrupt profile, path spaces, Android resume and offline legacy behavior.
- **Do not distribute** any synthetic fixture as gameplay save. Standalone tests generate sector footer mock data which intentionally cannot be used in the game.

### Known limitations and rollback

The manager only validates flash slot structure, **not checksums or semantic integrity**; filenames and metadata are not yet Unicode-safe on all Windows installations. Backups need safe post-commit hooks and verified recovery before the feature can be advertised as resilient to crashes. Invalid save path fail-closed is the intended behavior, not an attempt to fix corrupted saves.

Rollback: use unchanged user-tested branch `feature/lan-v0721-viewport-culling`; current branch `feature/lan-v080-m0-m1-foundation` must stay experimental until real QA.
