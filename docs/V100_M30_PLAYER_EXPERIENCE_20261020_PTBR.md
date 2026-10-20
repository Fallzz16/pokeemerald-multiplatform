# Emerald Hybrid M3.0 — Experiência real do jogador (20/10/2026)

## Escopo

Somente o **multiplayer do Pokémon Emerald já existente**. Nenhum novo mapa, Pokémon, item, missão ou história. O **QA Lab / QA_A / QA_B permanece EXCLUSIVAMENTE para desenvolvimento**, não é interface nem dependência do jogador. Saves individuais, offline, Cable Club P2P e código de gameplay original são preservados.

Branch desta implementação: `feature/emerald-m30-player-journey-20261020`, criada da revisão BETA15 `2dd8dd78867408ec17a445de30fcdcd7037a10c6` (PR #27). PR novo deve permanecer DRAFT e ter PR #27 como base. **Não mesclar ou publicar beta sem testes humanos.**

## O que um jogador realmente verá nesta atualização

### 1. Tela inicial do launcher Windows

**Três escolhas principais:**
- **JOGAR SOZINHO**: abre `pokeemerald.exe` com seu perfil local, sem conectar rede.
- **CRIAR SALA**: confirma PIN privado (se vazio, gera PIN de seis dígitos), inicia o servidor EHL8 pareado e abre automaticamente **o próprio jogo do anfitrião** conectado à sala pelo loopback `127.0.0.1`. **O launcher NÃO é minimizado** porque o anfitrião ainda precisa iniciar a sala.
- **ENTRAR NA SALA**: lê IP numérico, porta e PIN do formulário; abre `pokeemerald.exe` com `--session-client`, `--session-pin-stdin` e `--session-wait-for-start`, aguardando o anfitrião. **Nunca entra acidentalmente no Cable Club antigo** devido a checkboxes técnicas.
- **MODO CLÁSSICO P2P**: hospedagem/entrada antiga permanecem acessíveis em uma seção avançada separada, para a infraestrutura Cable Club já existente; não confundir com a sala de presença EHL8.

### 2. Tela de espera e sala

Enquanto o servidor não iniciou a partida, a janela real do Emerald exibe um painel sobre o jogo existente:

```text
          SALA ONLINE

       AGUARDANDO AMIGO
       HOST INICIA SALA
```

Se falhar a conexão antes do START:

```text
          SALA ONLINE

        CONEXAO FALHOU
        FECHE E REENTRE
```

O painel é desenhado em SDL2 usando apenas pequenas fontes bitmap 3x5 locais e primitivas de desenho. Ele usa o estado atômico da conexão já presente na versão anterior; **não bloqueia renderização, relógio, rede, scripts ou salvamento, mas os controles de gameplay continuam bloqueados até START** (controle já testado pelo usuário anteriormente). Depois de receber START, o painel some e o jogo volta a receber controles; queda posterior de rede não congela a aventura solo.

### 3. O anfitrião inicia a partida

O launcher aberto mostra estado humano derivado do snapshot EHL8 atômico:

- Sala iniciando / sala 1/2 aguardando amigo.
- Sala 2/2, prontos 1/2 — preparando a partida.
- Sala 2/2, prontos 2/2 — **INICIAR PARTIDA** habilitado.
- Sala já iniciada, ou vaga reservada para reconexão — iniciar de novo permanece desabilitado.

Se o jogo local não conseguir abrir, o processo do servidor recém-criado é encerrado pelo launcher, para não deixar uma sala órfã. Botões **GERAR PIN** e **VER PIN** funcionam localmente, sem enviar PIN em argv ou guardar em configurações; **COMO CONVIDAR** explica o uso do IPv4 privado e VPN sem publicar portas na WAN.

## Arquivos alterados

- `tools/emerald_launcher.py`: a tela de seleção, geração/visibilidade do PIN, criação e autoentrada do anfitrião, texto de ocupação, instruções de convite, preservação do modo P2P avançado e tratamento de falhas de inicialização.
- `src/lnet/lnet_wait_overlay.h`: NOVO renderizador simples da sala EHL8 para a janela real do Emerald, sem libs/fontes externas.
- `src/platform/sdl2.c`: inclusão e chamada exclusiva quando `--session-wait-for-start` está ativo, antes de `SDL_RenderPresent`.
- `scripts/verify_v080_profile_patch.py`: reversão estrita apenas dessas duas inserções no SDL2 antes da comparação com o hash da versão protegida. **O verificador não foi desativado.**
- `tests/test_emerald_launcher.py`: teste de entrada na sala correta, convite, status, geração de PIN, autoentrada local e rollback de host caso o jogo falhe.
- `tests/test_ehl8_wait_overlay.c`: NOVO teste em C, com renderer SDL falso para garantir que overlay só desenha em WAIT/FAILED e fica dentro do viewport original 240×160.
- `.github/workflows/emerald-auto-qa.yml`: executa teste de overlay no Linux e observa alterações no novo header.

**Removidos:** nenhum arquivo ou sistema legado. **Não alterados:** SAVE format, batalha/troca Cable Club, rede binária EHL8, servidor Python, Android, gameplay de NPCs e mapas, QA Lab.

## Como validar antes de aceitar

1. Compilar Windows no SHA final; inspecionar artefato ZIP portátil e SHA. Não confundir Auto QA com tela realmente vista em um PC.
2. Abrir o launcher no Windows e conferir que há três botões: Jogar sozinho, Criar sala e Entrar na sala. Criar/selecionar perfil de TESTE.
3. Clicar **CRIAR SALA**, gerar PIN, verificar que servidor abre e que o Emerald do host conecta ao IP local. Confirmar que launcher permanece acessível para START.
4. Na segunda instância/PC, selecionar **ENTRAR NA SALA**, informar IP privado/porta/PIN e verificar que o fluxo é EHL8, não antigo P2P.
5. Confirmar ambos vendo o painel SALA ONLINE e com botões bloqueados enquanto esperam 2/2.
6. Quando o launcher marcar **2/2 prontos**, clicar **INICIAR PARTIDA**. O painel deve desaparecer de ambos, e jogos devem responder aos botões.
7. Usando saves QA distintos, colocar personagens no mesmo mapa e confirmar presença e movimento dos dois lados; testar desconexões/transições/saves separadamente.
8. Criar sala com PIN incorreto, abortar antes de START e simular falha de criação para conferir que não ficou processo órfão; nenhum PIN deve aparecer em logs/argv.
9. Abrir **JOGAR SOZINHO** e **modo clássico P2P**: não pode aparecer tela de sala online nem impedir controles nesses modos.

**Limites e honestidade:** o painel no jogo é uma tela de espera **sobre a imagem do Emerald**, não uma nova scene da engine GBA. Não é um menu interno de seleção de perfil, não oferece pronto/cancelar individual dentro do jogo. Ainda não comprova sprites de dois PCs, batalhas/trocas EHL8, Android ou crossplay. É o primeiro incremento voltado ao consumidor final, mantendo o QA Lab separado.

**Rollback:** pacote original do PR #27 commit `2dd8dd78867408ec17a445de30fcdcd7037a10c6`; extrair em pasta isolada, não substituir saves; PR draft da nova branch não deve ser mesclado até CI e QA humano.
