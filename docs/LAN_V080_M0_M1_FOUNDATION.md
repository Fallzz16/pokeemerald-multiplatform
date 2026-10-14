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
| `.github/workflows/test-lan-v080-foundation.yml` | Linux normal/sanitizers e cross-compilação Windows x86 |

O teste de save **gera arquivo sintético temporário de cabeçalhos**, que não é jogável. **Nunca distribuí-lo como save real**. Os testes não leem, não criam nem alteram saves do usuário.

## Testar

```bash
bash scripts/verify_lan_v080_foundation.sh
SANITIZE=1 bash scripts/verify_lan_v080_foundation.sh
```

Resultados esperados no Linux:
- 192 testes de roundtrip, mais rejeição de pacotes inválidos: PASS
- Importações intactas, locks, backup/restore/retention, corrupção simulada: PASS

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

- Branch desta fundação: `feature/lan-v080-m0-m1-foundation`, PR experimental a criar contra `feature/lan-v080-architecture-spec`.
- Baseline de gameplay validado pelo usuário: `feature/lan-v0721-viewport-culling`, commit `a87e2c49e453db32def5e71ba2a2e696a911d504`.
- **Nenhum código pré-existente foi alterado:** basta não mesclar a branch para manter o jogo idêntico.
- `AI_README.md` é documento obrigatório de transferência entre IAs, com registro do que se implementou e do que ainda não foi.
