# LAN Overworld — Especificação técnica da próxima etapa

> **Não implementado nesta branch.** Prioridade atual: estabilizar o Cable Club (batalhas e trocas) e validar dois jogadores em jogo real antes de ativar sincronização no mapa.

## Objetivo do primeiro incremento

Dois jogadores em uma rede local conseguem **ver o sprite um do outro e acompanhar movimentos** no mesmo mapa de Hoenn. Não se pretende sincronizar NPCs, encontros selvagens, história, clima, inventários ou estado de missões no primeiro incremento.

**Regras do primeiro lançamento:**
- Exatamente **2 jogadores**, host e cliente; mesma compilação Hybrid compatível.
- Personagem remoto sem colisão, sem bloquear portas/warps, sem participar de scripts de NPC e **sem ser salvo** como evento persistente.
- Mostrar o personagem somente quando os dois estão no mesmo `mapGroup/mapNum`, dentro de um estado de campo compatível; remover ao trocar de mapa, iniciar batalha, desconectar ou retornar ao menu.
- Reutilizar gráficos de treinador já existentes e direção/andada/corrida sem adicionar sprites ou texturas grandes.
- Estados locais e saves continuam independentes. Nenhuma alteração em `SaveBlock1`/`SaveBlock2`.

## Arquitetura recomendada

### 1. Separar Cable Club e presença no mapa

O canal do Cable Club atual usa **troca de palavras SIO de 16 bits** pelo TCP. Não misturar pacotes de movimento dentro dessas palavras: isso arriscaria checksums, filas de link, batalhas e trocas.

Para o protótipo, usar um **segundo canal TCP exclusivo de presença** na rede local, porta configurável `45681` (padrão `45680 + 1`). A configuração deve reaproveitar papel host/cliente e IPv4 da conexão principal, mas o ciclo de vida da sessão de presença é independente. Não conectar a internet pública.

### 2. Pacotes de presença, validação e limites

Criar protocolo versionado com `magic`, `version`, `kind`, `payload_size`, `sequence` e informações compactas:
`mapGroup`, `mapNum`, `tileX`, `tileY`, `facing`, `movementState`, `appearanceId`, `activity` (field/battle/menu/warp).

- Verificar comprimento/versão antes de consumir; rejeitar mensagens inválidas e posições fora dos limites do mapa.
- Emissor transmite no máximo **10 snapshots por segundo** ou ao mudar de mapa/direção/estado, sem depender da taxa de fast-forward.
- Receptor descarta sequências antigas e usa pequena fila limitada (últimas ~3 poses).
- Se o peer ficar ~1s sem pose, parar animação; após ~3s, ocultar sprite até nova pose válida. Sem bloquear a thread de renderização.
- Não transmitir informações de save, IDs pessoais, inventários, equipes ou conteúdo de scripts.

### 3. Integração com os sistemas Emerald existentes

Mapas: `gSaveBlock1Ptr->location.mapGroup/mapNum`, `gMapHeader`; posição local usando os helpers de coordenadas do player e levando em conta `MAP_OFFSET`.

Sprites/objetos: estudar `src/event_object_movement.c` e `include/event_object_movement.h`. Um personagem remoto não deve reutilizar `localId` que pertença a NPC de mapa, nem ser registrado em um `ObjectEventTemplate` salvo. Criar um objeto/sprite transitório reservado (ou um renderer específico), com limpeza explícita em warp, batalha, mapa inexistente e desconexão.

Movimentos: interpolar no espaço do mapa em passos curtos, preservar direção cardinal e usar animações do gráfico selecionado. Na fase inicial não replicar bicicleta, Surf/Dive, quebra-cabeças, Cut/HM ou colisão com NPCs.

### 4. Interface mínima

Estado na UI: **Offline, Aguardando, Conectado, Jogador no mesmo mapa, Jogador em outro mapa, Conexão perdida**. Não abrir menus intrusivos a cada pacote. Opcional: nome do jogador no HUD (sem alterar as sprites originais).

### 5. Segurança de concorrência

A rede deve ser feita por polling com quotas de bytes/frames, nunca dentro de callbacks de VBlank ou renderização. A atualização da pose e manipulação de sprites ocorre na **thread do jogo**, não na thread de socket. O personagem remoto nunca modifica as coordenadas/câmera do player local.

## Matriz de aceite de mundo visível

1. Host e cliente no mesmo mapa: cada um enxerga o outro e suas direções.
2. Caminhada e corrida em sequência: movimentos suaves, sem "teleportar" sob jitter moderado.
3. Personagens em mapas diferentes: remoto invisível. Volta a aparecer ao entrar no mesmo mapa.
4. Warp, batalha, pause/menu: sem sprite persistente em local incorreto.
5. Queda de Wi-Fi ou encerramento: personagem remoto desaparece e a sessão offline local continua.
6. 20 minutos em Hoenn: sem crescimento de memória, travas, perda perceptível de FPS ou gravação inconsistente.
7. Desempenho no Windows x86 e Android ARMv7, incluindo fast-forward e retorno de app do background.

## Ordem de execução

- **Etapa A (agora):** Cable Club completando uma batalha e uma troca com dois saves de teste; validação de regressão de inicialização, desconexão, áudio, UI e estabilidade.
- **Etapa B:** codec e testes de protocolo de presença, sem mexer no gameplay.
- **Etapa C:** sprite remoto visível + sincronização de posição/direção no mesmo mapa (Windows).
- **Etapa D:** transições e desconexão + Android e interoperabilidade.

Somente abrir PR para a **Etapa B** após a validação funcional da **Etapa A**. Não anunciar o multiplayer overworld como disponível antes da Etapa C/D aprovada.
