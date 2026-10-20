# Emerald Hybrid M3.0 — MEGA atualização online, gates de beta (2026-10-19)

**Objetivo aprovado:** entregar numa **única linha de release beta** um Emerald existente com multiplayer online de verdade: dois Windows, batalha/troca, saves seguros, Lobby humano, jogo com amigo em outra casa (via rede privada) e, quando validado, Android/crossplay. Nada de mapa, história, missões, Pokémon, torneios ou conteúdo novo. Laboratório QA_A/QA_B continua ferramenta de DESENVOLVIMENTO, separada do launcher.

**Escopo não significa que todos os seis marcos já foram implementados.** Este arquivo é plano + registro de QA e limiares de aceite, não nota de lançamento.

## Política de implementação segura — uma versão beta, vários gates obrigatórios

| Gate | Aceite verificável | Situação em 19/10 | Não confundir |
|---|---|---|---|
| G0 — base | CI Windows completo, jogo+Lab+launcher pareados com hash e rollback | Preview anterior aprovado no CI, QA humano pendente | Compilar ≠ jogar |
| G1 — exploração 2 PCs | Dois clientes Emerald em dispositivos distintos, personagem remoto sincronizado, sala que aguarda START, saída/reconexão, saves individuais sem corrupção | **Parcial**: EHL8 já tem protocolo e sprite; novo launcher implementa START com hash e teste automatizado; precisa QA de jogo real | 2 bots não são 2 jogadores |
| G2 — batalha | Na mesma sala EHL8, jogador A convida B, B aceita/recusa, partida 1v1 baseada em Cable Club já existente, resultado e retorno corretos | **Não implementado** | P2P antigo não é batalha EHL8 |
| G3 — troca | Convite/inspeção/duplo aceite, commit sem duplicação, desconexões não produzem duas cópias divergentes, saves originais recuperáveis | **Não implementado** | Cópia de backup não substitui transação |
| G4 — saves | SHA de pacote e arquivos, backup atômico, byte-match da cópia temporária, controle exclusivo de perfil e validação real dos checksums por tamanho de setor | **Parcial**: verificação byte-a-byte adicionada; checksum interno por setor ainda falta | Estrutura/cópia idêntica não significa save semanticamente íntegro |
| G5 — rede privada | LAN e duas casas via conexão privada com IP manual, porta 45680, host não exposto publicamente, manual de diagnóstico | **Manual disponível**; infraestrutura real ainda deve ser testada | PIN 6 dígitos não protege WAN |
| G6 — Android/crossplay | APK Android ARM64 instalável, save Android separado, toque/controle, sessão Windows ↔ Android, mesmos protocolos, reconexão | **Não implementado/validado** | APK v0.7.2.1 ARMv7 é outra geração do projeto |

**Aceite M3.0:** só rotular "BETA JOGÁVEL" depois de G1, G2, G3, G4 e G5 em QA real. Android/crossplay (G6) pode ser beta secundária, com rótulo explícito, mas faz parte do objetivo da MEGA atualização — não declarar sem teste.

## Fase implementada nesta branch de integração

- Launcher Windows final (NÃO Lab): se `EHL8_M23_GAME_MATCHED.txt` existir, verifica SHA256 real de `pokeemerald.exe` e `EmeraldSessionServerM23.exe`, recusa arquivos misturados; inicia o servidor com `--pin-stdin --admin-stdin --host-start --resume-v1`, mantém pipe privado e **INICIAR SALA (2/2)** só habilita com `EHL8_ROOM_COUNT=2/2` e `EHL8_READY_COUNT=2/2` e sala ainda não iniciada. Envia `START` por stdin local (não protocolo TCP). UI acompanha prontidão pelo log do próprio servidor. Com ZIP antigo sem marcador M23 mantém fluxo legado de START automático.
- Save manager `src/profile/save_profiles.c`: compara byte-a-byte origem e cópia temporária antes de commit atômico em importação/backup/restore. Não calcula checksums internos, não altera mapa ou save no formato.
- Testes Python da lógica do launcher e native C de saves no Linux; o workflow Auto QA monitora mudanças em launcher/saves. Servidor e cliente não receberam novos tipos de mensagens neste incremento.

## Teste com máquinas independentes — o que pedir ao usuário

**Preparação:** a mesma revisão/ZIP em duas pastas novas, cada máquina com um perfil QA descartável, backups fora do ZIP. No pacote ver `REVISAO_EXATA.txt` e `SHA256_COMPONENTES.txt`; nunca misturar executáveis M2.2/M2.3.

**Mesmo Wi-Fi:** Host abre `EmeraldLauncher.exe`, define PIN de seis dígitos e porta 45680, clica CRIAR SALA. O jogo dele entra no EHL8 em `127.0.0.1`; convidado entra em `IPv4 privado do host:45680` e mesmo PIN. Verificar 0/2→1/2→2/2, "Prontos 2/2" e botão INICIAR SALA. **Esperar 30 s antes de START**. Só o host pode iniciar; depois verificar sprite B, movimento, câmera, portas, batalhas selvagens individuais e continuidade solo. Não testar batalhas/trocas via EHL8 até implementadas.

**Máquina virtual Windows:** rede **Host-Only** para host↔VM ou bridge em LAN privada. Dois launchers normais, saves separados; laboratório não controla o cliente remoto. VM não substitui dois PCs reais nem valida a qualidade da Internet.

**Outra casa:** usar **Tailscale com compartilhamento apenas da máquina anfitriã** e regras de acesso restritas; trocar somente o IPv4 Tailscale do servidor e PIN com amigo confiável. Não abrir portas no roteador, não instalar bridge WAN insegura, não postar PIN, IP pessoal, IDs ou saves em público. Instruções de referência: https://tailscale.com/docs/use-cases/personal-or-at-home-use/share-private-game-server e https://tailscale.com/docs/features/sharing .

**Diagnóstico não invasivo:** no Windows, verificar processo EmeraldSessionServer.exe/M23 no Gerenciador de Tarefas; opcionalmente `netstat -ano | findstr :45680` e teste privado `Test-NetConnection ENDERECO_IP -Port 45680`. Não encerrar processos desconhecidos, não usar `0.0.0.0` como IP de destino; se bloqueado, ver regras do Firewall do Windows **somente para redes privadas/Tailscale e executável correto**. Guardar logs (sem PIN/saves reais) para reproduzir defeito.

**Checklist humana obrigatória:** servidor 0/2 sem jogos; 1/2 após primeiro; 2/2 READY após segundo; 30s sem START; click host START; sprites e movimento bidirecionais; troca de mapa; saída e reentrada; perda breve da rede/reconexão; save de ambos; fechar launcher/servidor/VM; abrir cada save OFFLINE. Se falhar, registrar SHA, passo exato, prints e logs anonimizados.

## Planejamento de integração PvP/troca (sem fingir que já existe)

- Manter **EHL8 como control plane**: presença, identidade, pedido de interação, aceite/recusa, expiração e estado; mensagens novas exigem revisão versionada do protocolo C/Python e regressões de compatibilidade.
- **Data plane P2P/relay** reutiliza serial/link game engine atual: ao aceitar batalha/troca, estabelecer sessão Cable Club existente por par, sem enviar bytes seriais cegamente por canal de posição EHL8; depois retornar ao mapa. Segurança/timing de NAT precisam ser avaliados; não assumir que UDP/TCP existente atravessa roteadores.
- **Troca transacional:** copiar saves isolados antes, reunir os dois aceites, registrar `tx-id`, garantir commit único ou rollback/recuperação se rede cair; testes de desconexão em cada fase e evitar duplicação. Nenhuma troca real sem esses testes.

## Viabilidade Android confirmada pelo código

O Gradle do projeto restringe `abiFilters 'armeabi-v7a'`; o CMake tem objetos gráficos/sonoros montados com `arm-none-eabi-as -march=armv7-a`. Esses objetos de 32 bits **não podem ser vinculados diretamente a um binário ARM64**. A rota correta é criar pipeline de dados independente de ABI ou recompilar com toolchain/assembler adequado ao target, migrar build Android para `arm64-v8a` **sem retirar ARMv7 antes do teste**, testar APK real e só então implementar EHL8 no launcher Android e crossplay. Fonte: https://developer.android.com/ndk/guides/abis .

## Critérios de encerramento / rollback

Não efetuar merge/release antes de CI concluído e QA humano. Se o launcher manual falhar, reverter ao preview do PR #21 no commit `476f56cfd0d7e2782e6b87e63c4d7443a1207a87` em pasta separada. Nunca substituir pastas de saves de QA/release; guardá-los separados. `AGENTS.md` exige atualização de `AI_README.md` por incremento com SHA+testes+limites.
