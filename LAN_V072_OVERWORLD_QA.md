# Emerald Hybrid LAN v0.7.2 — Personagem remoto em Hoenn (experimental)

## Mudanças implementadas

- **Canal separado:** o SIO do Cable Club continua na porta definida pelo usuário (padrão TCP 45680); o mundo utiliza **TCP 45681** (`porta do link + 1`).
- **Dois jogadores:** recebe pose com grupo/número do mapa, tile X/Y, direção, sexo/aparência e elevação.
- **Sprite virtual temporário:** usa `CreateVirtualObject`, sem bloquear jogadores, sem executar scripts, sem persistir em qualquer save.
- **Visibilidade:** o amigo aparece apenas no mesmo mapa do personagem local e enquanto ambos estão na exploração normal, fora do Cable Club. Em mapas diferentes, batalha ou desconexão, desaparece.
- **Movimento:** pacotes de 18 bytes a cada ~100 ms; posição interpolada (máximo 3 pixels por frame); animação original GBA para caminhar e olhar.
- **Robustez:** read/write TCP não bloqueante, 3 mensagens recebidas no máximo por frame, validação estrita do protocolo, sequências antigas descartadas, posição remota expira após 3 segundos.

**Estado:** candidato em desenvolvimento. O funcionamento real do sprite e da transição de mapas depende de testes Windows/Android. Não afirmar que está funcionando em jogo antes de executar estes testes.

## Como testar no Windows

1. Use **a compilação Windows desta branch**, não o ZIP da Release v0.7.0, pois os arquivos antigos não contêm o mundo compartilhado.
2. Tenha duas cópias do jogo em diretórios separados, com saves de teste compatíveis e independentes.
3. Na pasta host: `pokeemerald.exe --lan-log host.log --lan-host=45680`
4. Na pasta cliente do **mesmo PC**: `pokeemerald.exe --lan-log cliente.log --lan-client=127.0.0.1:45680`. Em PCs diferentes, use o IPv4 local do host.
5. Conecte host/cliente, **sem entrar no Cable Club**, e coloque os dois treinadores na mesma cidade/rota ou mesmo interior. Um sprite virtual representando o outro deve aparecer.
6. Ande e corra, vire e entre/saia de construções. Ao se separar em mapas diferentes, o remoto deve desaparecer sem travar.
7. Feche o cliente; o sprite deve sumir. Depois teste batalha e troca no Cable Club, verificando que as mudanças não afetaram a camada serial original.

**Rede:** em dois PCs ou PC+Android, autorize entrada TCP **45680 e 45681** apenas na rede privada confiável do host; não exponha essas portas à internet. Se houver isolamento de Wi-Fi, a comunicação pode falhar.

## Limites deliberados da v0.7.2 inicial

- Sem mapa/savestate compartilhados, NPCs, eventos, scripts, encontros selvagens ou saves sincronizados.
- Sem colisão com o amigo.
- Sem replicação detalhada de bicicleta, Surf, Dive, pulos ou animações especiais; usa sprite de treinador normal e caminhada básica. Suporte completo vem depois dos testes.
- Sem reconexão automática após erro persistente do canal de presença: reinicie a sessão host/cliente.
- Posição remota é uma interpolação simples por tile, não predição de movimentos. Fast-forward pode causar saltos no movimento.
- Um cliente que não consegue conectar na porta de presença pode ainda usar o Cable Club pela porta original.

## Plano de verificação

- [ ] **TCP:** `bash scripts/verify_lan_foundation.sh` aprova os testes de pacote, ligação e desconexão.
- [ ] **Windows:** GitHub Actions produz o executável desta branch.
- [ ] **Android ARMv7:** GitHub Actions produz o APK desta branch.
- [ ] **Windows x2 real:** ver treinador, mover, entrar em outro mapa, verificar ocultação e reaparecimento.
- [ ] **Crash/save:** salvar/reabrir durante/apos sessão; nenhum NPC/mapa salvo a mais.
- [ ] **Regr. Cable Club:** batalha e troca completas como na versão anterior.
- [ ] **Dispositivo Android real:** instalação, exploração conjunta, suspensão/reabertura do app e perda de Wi-Fi.

## Como reportar problemas

Anexar `host.log`, `cliente.log` (se usar Windows), captura das duas telas, plataformas, tempo até o problema, mapa local/remoto e se as portas 45680 e 45681 estavam abertas.

**Importante:** não juntar esta branch à versão estável sem a matriz de testes. Código-fonte e documentação: `feature/lan-v072-overworld-presence`.
