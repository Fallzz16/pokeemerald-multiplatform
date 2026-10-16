# Emerald Hybrid v1.0 — M2.2-A: reserva autenticada de 60 segundos

**Status: protocolo e ferramenta de diagnóstico candidatos a QA. Não é
reconexão automática do jogo.** Branch isolada
`feature/emerald-v100-m22-reconnect-core`, derivada de M2.1-B.

## O que está implementado no servidor

- Novo tipo de pacote EHL8 `18 RESUME` **opcional**; cabeçalho original
  de 28 bytes, versão 1.0, PIN e demais mensagens continuam inalterados.
- **Desligado por padrão.** A opção `--resume-v1` só deve ser usada com
  clientes atualizados. O Emerald jogável atual NÃO entende o pacote 18:
  iniciar o servidor com essa opção durante partidas antigas causa desconexão.
- O servidor entrega token criptograficamente aleatório de 32 bytes após JOIN.
  Se o TCP cair durante GAME, ele reserva a mesma vaga por 60 segundos, mesmo
  que outro jogador permaneça conectado. Um novo jogador não pode tomar a vaga.
- Retomada exige PIN + identidade do perfil + token original, enviados via
  conexão TCP EHL8. A vaga restaurada recebe novo token (o anterior deixa
  de funcionar); novos JOINs permanecem bloqueados quando a sala está trancada,
  mas uma retomada autenticada é autorizada.
- Comandos de administrador continuam pelo stdin privado. KICK em um perfil
  desconectado revoga sua reserva. LEAVE normal, KICK e erro de protocolo
  não dão direito à reserva.
- Após o vencimento, a vaga é liberada para um novo perfil. Nada é salvo
  em disco: tokens existem apenas em RAM e não aparecem nos logs.

## Como testar agora (sem arriscar as partidas)

1. Baixe o complemento Windows M2.2-A das Actions da branch acima.
2. Extraia o ZIP em **pasta separada**; não é necessário instalar por cima
   da preview M2.1-B. O kit inclui `EmeraldQAReconnect.exe` (interface
   gráfica, sem CMD), `EmeraldSessionServerM22.exe` e instruções.
3. Abra **EmeraldQAReconnect.exe** e clique
   **EXECUTAR TESTES DE RECONEXÃO**.
4. Aguarde a tela apresentar testes concluídos, 0 falhas e 0 erros.
   A suíte abre sockets apenas em `127.0.0.1`, na porta efêmera fornecida
   pelo sistema; usa perfis simulados, não inicia `pokeemerald.exe`.
5. Consulte o relatório em
   `%LOCALAPPDATA%\EmeraldHybridV1QALab\reconnect\resume-qa-*.json`.
   Se houver erro, envie esse JSON e um print da janela.
6. Mantenha usando normalmente a versão M2.1-B e seus saves. Não renomeie
   `EmeraldSessionServerM22.exe` para `EmeraldSessionServer.exe`.
   Não ligue `--resume-v1` no seu jogo atual.

## Testes automatizados e limitações

- `tests/test_ehl8_resume_v1.py` valida no servidor real: geração do token,
  queda do socket, retenção do slot, negação de entrada sem token, retomada
  durante LOCK, token rotativo/antirreplay, expiração, revogação via KICK.
- Suítes antigas `test_emerald_session_server.py` e
  `test_emerald_session_admin.py` são executadas no mesmo workflow, em
  Windows e Linux, para detectar regressões do EHL8.
- Esses testes não comprovam uma reconexão automática no `pokeemerald.exe`;
  o cliente C nativo ainda encerra ao perder a conexão. Isso é o **M2.2-B**.
- A expiração na suíte é acelerada via relógio do teste para evitar esperar
  60 segundos; o valor real padrão de produção é 60 segundos e deve ter
  regressão adicional em QA de longa duração.
- O EHL8 continua apenas para LAN/VPN confiável, **não é TLS**, PIN de 6
  dígitos não substitui autenticação forte de acesso externo.
- Se alguma suíte ou build falhar, esta entrega permanece EXPERIMENTAL.
- Todos os saves, Cable Club, sprites, perfis e launcher M2.1-B são mantidos.

## Próximo marco M2.2-B

Atualizar o `src/lnet/lnet_session_client.c` para armazenar o token somente
em RAM, tentar reconectar por até 60 segundos com backoff, restaurar a mesma
sessão e exibir mensagens claras. A integração deverá reconstruir o jogo
para Windows em um pacote fechado com servidor compatível, conferir as cores
da May (correção visual aprovada) e realizar QA humano com dois jogos.

**Rollback:** branch de desenvolvimento M2.1-B
`feature/emerald-v100-m11-50bots-lab` (commit `2d0cb13`).
