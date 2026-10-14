# Emerald Hybrid LAN v0.7.1 — Plano de teste e evidências

## Estado

Esta é uma **branch experimental de estabilização**, derivada de `feature/lan-v070-async-slot-hardening` (base `feature/lan-hybrid-v070`). Não substitui `emerald-hybrid-v0.7.0`, não é release final, e **não há comprovação de batalhas/trocas completas entre dois dispositivos** até que os testes descritos aqui sejam executados.

Branch: `feature/lan-v071-connection-stability`.

### Modificações desta etapa

- Sockets TCP de conexões LAN aceitas e iniciadas permanecem em **modo não bloqueante** depois do handshake. O transporte não depende só de `select()` para evitar espera na thread do jogo.
- A conexão via UI/CLI LAN aceita endereço **IPv4 literal**, sem resolução DNS bloqueante; IP inválido gera erro controlado.
- Deadlines de conexão, HELLO e transferência serial usam relógio de tempo decorrido monotônico (Windows `GetTickCount`, Android/Linux `CLOCK_MONOTONIC`) e diferença sem sinal para lidar com overflow do contador.
- `select()` que falhar passa a retornar erro em vez de ser confundido com uma tentativa que ainda está aguardando dados.
- Uma transferência serial parcial conserva o **valor original do SEND local** até finalizar (inclusive na composição do RECV/SIO), mesmo que o chamador apresente outro valor em tentativas posteriores.
- Os iniciadores `LAN_HOST.bat` e `LAN_JOIN.bat` agora criam automaticamente os logs `lan-host.log` e `lan-cliente.log`.
- Testes nativos adicionados/atualizados: dados atrasados, mudança do valor local durante slot pendente, rejeição de IPv4 inválido e encerramento do outro jogador no meio do slot.

### Executar verificação técnica

```bash
bash scripts/verify_lan_foundation.sh
EMERALD_LAN_QA=1 bash scripts/verify_v070.sh
```

Os workflows Windows e Android desta branch devem ser executados no GitHub Actions. **Resultados de builds anteriores não validam automaticamente o commit atual.** Uma falha de CI na instalação de pacotes anterior ao build deve ser distinguida de erros de compilação/código.

## Aceite funcional — ordem sugerida

1. **Offline:** iniciar cada plataforma, entrar no jogo, movimentar-se, conversar com NPCs, verificar menus, áudio, fast-forward e carregar/salvar dados em um save de teste.
2. **Windows + Windows:** iniciar `LAN_HOST.bat` em um PC e `LAN_JOIN.bat` em outro, ambos com **o mesmo build**; anotar o IPv4 local de host e porta 45680/TCP.
3. Confirmar que host e cliente enxergam a sessão e finalizam o **handshake serial** entrando no Cable Club (não basta o log dizer que TCP conectou).
4. Completar uma batalha com pelo menos duas ações por lado, troca de Pokémon em combate, finalização e retorno ao mapa. Salvar e reabrir os dois saves.
5. Completar uma troca real: validar espécies, nomes, OT, itens e inventário em **ambos** os lados depois de salvar e reabrir.
6. Testar cancelamento, fechamento do host, interrupção do Wi-Fi, IP inválido e atrasos. Nenhum resultado pode exigir reset forçado sem uma forma de recuperar o save.
7. Repetir para Android + Android, Windows + Android e Android + Windows. Android é `armeabi-v7a` (32 bits); celulares exclusivamente ARM64/64 bits podem não instalar a versão atual.

## Evidências a coletar

| Etapa | Evidência mínima |
|---|---|
| Connect TCP | `lan-host.log`, `lan-cliente.log` e IPv4/porta (ocultar IPs públicos) |
| Handshake do jogo | Trecho dos logs, captura de tela do Cable Club nas duas instâncias |
| Batalha | Capturas no início e fim, comandos executados e retorno ao mapa |
| Troca | Pokémon antes/depois e validação após save/reload dos dois jogadores |
| Desconexão | Momento de perda da rede, mensagem exibida e comportamento da UI |
| Android | Versão do Android, CPU/ABI, gravação ou capturas, `adb logcat` se possível |

Faça **backup de `pokeemerald.sav` no Windows**. No Android, os saves ficam no armazenamento privado do app: não desinstale um APK debug sem método confirmado de recuperar os saves. Chaves de assinatura podem mudar entre builds.

## Critérios de bloqueio para merge/release

- Falha nos testes nativos, regressões v0.7.0 ou builds Windows/Android.
- Menu Cable Club não completa handshake, batalha ou troca.
- Congelamento persistente, buffer/queue overflow, dados de Pokémon inconsistentes, danos ao save ou grande degradação de FPS.
- Latência por palavra SIO ainda pode criar pausas: avalie um protocolo de slots em lote **apenas após medir** dados reais. Não apresente sincronização de mapa/mundo compartilhado como implementada.

**Importante:** esta branch não inclui o mundo compartilhado de Hoenn. Isso será uma fase posterior quando o multiplayer do Cable Club estiver validado.
