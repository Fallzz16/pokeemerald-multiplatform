# Emerald Hybrid v0.8 — Reconexão LAN dedicada (M2/4 experimental)

**Branch:** `feature/lan-v0804-reconnect-hardening`; **PR #14 (draft)** contra `feature/lan-v0803-dedicated-session-core`. Esta etapa modifica somente o caminho **EHL8 dedicado**, sem alterar os saves ou os canais P2P Cable Club antigos. A instalação v0.8.2 comprovada pelo usuário não é modificada.

## Decisões aprovadas que esta revisão atende

- #60A: manter a vaga por 60 segundos após queda inesperada.
- #86A: tentar reconectar automaticamente durante a reserva, comunicando o estado ao sistema de logs existente.
- #77A/#40A: impedir sessão simultânea com mesmo identificador de perfil; ao cair, apenas o mesmo perfil pode recuperar a vaga.
- #59B/#87B: servidor vazio fecha após 15 minutos por padrão, **contados depois** que a última reserva de 60 segundos expirar.
- #100A/#116A: validar dois clientes dedicados antes de ampliar para três e quatro.
- #81A: sem conta online obrigatória. IDs de perfil + PIN são proteção operacional simples, **não prova de propriedade nem credencial segura para internet pública**.

## Implementação

### Servidor Python `tools/emerald_session_server.py`

- `reservations: profile_id -> (slot, monotonic_expiry)` apenas em RAM.
- Um socket que fecha ou cai sem protocolo `LEAVE` libera o avatar remoto **imediatamente** e reserva a vaga até 60 s.
- Um novo `JOIN` autenticado com mesmo profile ID recebe o **mesmo slot** se a reserva ainda estiver válida; terceiros continuam bloqueados de ocupar a vaga.
- `LEAVE` voluntário libera a vaga imediatamente, sem reserva, permitindo entrar com outro perfil.
- `sweep()` e `expire_reservations()` removem reservas expiradas. Não parar o servidor por inatividade enquanto existir reserva; quando a última expira sem jogadores, o cronômetro de 15 min começa nesse ponto.
- Uma parada explícita do administrador marca `stopped` antes de fechar conexões para não criar reservas fictícias.
- Não persiste PIN, poses ou dados de `.sav` no disco do servidor.

### Cliente nativo `src/lnet/lnet_session_client.{c,h}`

- Ao perder conexão depois de um JOIN válido, limpa o avatar remoto e entra em `EHL_CLIENT_RECONNECTING` (estado 7) com tentativa a cada 1,5 s, até 60 s no total. Se não retornar, entra em `EHL_CLIENT_FAILED` para continuar offline.
- Erros de formato/incompatibilidade/PIN incorreto continuam **fatais**, sem loop infinito de autenticação.
- Heartbeats a cada ~10 s, inclusive quando o avatar transmite posições continuamente (~10 Hz). Detecta ausência de qualquer resposta por 45 s; há janela de 60 s de nova conexão após detecção. A detecção de uma falha de Wi-Fi totalmente silenciosa não é instantânea.
- PIN só é conservado na memória do processo para autenticar a volta, não em argumentos, logs nem configurações; apagado no encerramento.
- Em saída voluntária tenta enviar `EHL_LEAVE` antes de fechar TCP. É best effort: se o último frame se perder, o servidor pode reservar até 60 s, comportamento seguro.
- Reutiliza exatamente o antigo sprite/culling via `src/link.c`; nenhum novo sprite nem qualquer reescrita de Quest UI/mapas.
- O TCP dedicado não substitui bytes de SIO de batalha/troca, que **não funcionam ainda através do servidor EHL8**.

## Testes obrigatórios

Testes de sockets sem arquivos de save:
- `tests/test_emerald_session_server.py`: perfil resgata seu slot, terceiro impedido durante reserva, reserva expira, cronômetro de inatividade reinicia corretamente, `LEAVE` libera de imediato.
- `tests/native_ehl8_client.c` aceita `--expect-reconnect` em modo QA.
- `tests/test_ehl8_native_bridge.py`: compila o cliente C; liga servidor Python + outro participante; força fechamento real do socket nativo no servidor; verifica retorno de mesma identidade e pose remota.
- Mantidos todos os testes M2 anteriores de handshake/READY, protocolo, PIN inválido e TCP legado.
- Workflows Windows/Android foram habilitados para compilar o jogo completo nesta branch. **Consultar resultados de GitHub Actions no SHA exato antes de afirmar aprovação.**

### Cenário manual no Windows (NÃO VALIDADO ATÉ AGORA)

1. Instale o candidato M2 em **pasta separada da v0.8.2**. Copie `.sav` válidos e distintos; nunca mova o único original.
2. Inicie servidor EHL8 dedicado; conecte 2 Emeralds usando perfis locais distintos.
3. Observe os dois personagens na mesma rota; desligue somente a rede Wi-Fi de um cliente por poucos segundos, mantendo o outro ativo.
4. O sprite do desconectado deve sumir; ao reconectar a rede antes do prazo, deve recuperar **a mesma vaga** sem reiniciar nem salvar automaticamente.
5. Tente entrar com um terceiro perfil durante os 60 s: deve ser recusado. Após a reserva expirar, o slot pode ser usado por outro.
6. Teste encerrar voluntariamente pelo menu e reabrir com outro perfil; se o sistema não conseguir entregar `LEAVE`, o atraso máximo de reserva permanece 60 s.
7. Teste deixar o servidor sem clientes até o prazo de inatividade configurado; não pode encerrar enquanto uma reserva válida existe.
8. Salve, feche e reabra cada aventura individual; compare com seus backups e quest status original. Não realizar trocas valiosas via dedicado.

## Limitações importantes

- Sem `resume token` criptográfico: PIN e ID de perfil podem ser copiados numa LAN maliciosa. Não abrir portas públicas nem afirmar segurança para WAN.
- Não há garantia de recuperação após reiniciar processo de servidor (reservas são memória volátil), queda mais longa que prazo ou internet de alta latência.
- O cliente ainda depende de testes visuais no hardware do usuário; CI de sockets e cross-compile não bastam para aprovar o modo de jogo.
- O cliente de mundo sincroniza apenas até dois participantes. Quatro, reconexão Android no app, lobby avançado, batalhas e trocas dedicadas seguem pendentes.
- Auto-backup depois de salvar manualmente, validação de checksums completos e verificação de shutdown permanecem trabalhos separados.

## Protocolo de atualização para outras IAs

Em qualquer atualização, registrar em `AI_README.md`: SHA exato, CI runs, mudanças adicionadas/modificadas/removidas, correções de testes, bugs reais, critérios ainda pendentes e rollback. Não reiniciar de zero, não mesclar PR #14 antes de QA satisfatório.

**Rollback:** branch `feature/lan-v0803-dedicated-session-core` contém o M2 anterior; `feature/lan-v080-mega-desktop-polish` tem instalador confirmado pelo usuário; v0.7.2.1 `feature/lan-v0721-viewport-culling` commit `a87e2c49e453db32def5e71ba2a2e696a911d504` foi testada no P2P. Nenhum save de usuário foi acessado nesta implementação.
