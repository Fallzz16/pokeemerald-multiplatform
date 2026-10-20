# Emerald Hybrid — BETA01D–BETA15D, engenharia e QA (20/10/2026)

> **Escopo restrito aprovado:** melhorar SOMENTE o multiplayer online do Emerald existente. Nada de histórias, missões, mapas, novos Pokémon ou expansões. **QA Lab (QA_A/QA_B) continua EXCLUSIVO de testes**, separado do launcher final. Modos offline e Cable Club P2P devem continuar funcionando. Estas 15 respostas são **todas D: decisões técnicas delegadas**, subordinadas às escolhas 1–116, 64D, EX01–EX64 (congeladas por escopo) e M3.0.

## 1. Declaração precisa do que foi decidido

Os códigos abaixo são uma **resolução técnica de 15 delegações**, não uma reprodução literal de enunciados do HTML anterior. O aceite depende de evidências. Não declarar algo implementado por ter sido apenas decidido.

| Código | Política técnica adotada | Gate |
|---|---|---|
| BETA01D | Preservar contrato EHL8 1.0 e isolamento absoluto do Cable Club P2P. | Protocolo |
| BETA02D | O anfitrião inicia a sala somente com 2/2 jogadores prontos, sem auto-START em modo administrado. | Lobby |
| BETA03D | O launcher lê um **snapshot atômico** do lobby, não combina logs de instantes diferentes; reservas para reconexão impedem START falso. | Lobby |
| BETA04D | Poses remotas com sequências e descarte de dados velhos; mostrar sprite apenas no mesmo mapa/câmera. | Gameplay |
| BETA05D | Reconexão até a janela de 60 s, sem corromper saves e sem congelar o jogador após START. | Rede |
| BETA06D | Verificar hashes do binário do jogo e do servidor antes de host administrado; preservar fallback de ZIP antigo sem marcador. | Pacote |
| BETA07D | Primeiro aceite de gameplay exige **duas instalações distintas Windows**, e o teste VM não substitui 2 PCs. | QA |
| BETA08D | Import/restore/backup copiam em temporário, sincronizam, comparam os bytes e **validam o temporário antes de substituir**; preservar .raw inválido para recuperação. | Saves |
| BETA09D | Checksums internos por setor só quando a estrutura efetiva do fork estiver confirmada e testada, sem offsets inventados. | Saves |
| BETA10D | Trocas precisam de confirmação dupla e recuperação transacional antes de poder trocar Pokémon em EHL8; não compartilhar .sav via servidor. | Troca |
| BETA11D | PvP deve reutilizar o mecanismo existente do Emerald com negociação explícita e integração de estados EHL8; não misturar bytes SIO no fluxo de poses. | Batalhas |
| BETA12D | Redes entre casas usam VPN privada e firewall restritivo durante a beta; PIN simples não torna o EHL8 seguro para porta WAN pública. | Segurança |
| BETA13D | QA Lab isolado com logs e teste real de dois clientes, incluindo espera >30 s sem START; usuário final não precisa abrir o Lab. | QA |
| BETA14D | Gerar ZIP Windows de SHA único com teste de extração/hashes e revisão humana antes de chamar de beta. | Release |
| BETA15D | Android ARM64/crossplay é o gate posterior ao Windows estável; não anunciar compatibilidade sem APK e hardware testados. | Android |

## 2. Revisão atual e alteração concreta

**Repo:** `Fallzz16/pokeemerald-multiplatform`.

**Base protegida:** branch `feature/emerald-m30-qa-start-gate-20261020`, SHA `745d40857a433933da112e5a5cd15f245cb81489` (PR #23). O usuário confirmou que **QA_A/QA_B aguardam START e liberam controles corretamente** no Windows. Isso comprova SOMENTE esse gate humano.

**Branch nova:** `feature/emerald-m30-beta15-reliability-20261020` (PR draft separado sobre a branch de PR #23). Não mesclar automaticamente. Reverter diretamente à revisão base de SHA `745d408` se necessário, em pasta separada de saves.

### Defeitos demonstrados no código e corrigidos neste lote

**A. Estado incoerente do launcher por logs de momentos diferentes.** O launcher antigo coletava o último `ROOM_COUNT`, `READY_COUNT` e `ROOM_STARTED` separadamente. Entre desconexão, queda, reserva de vaga e novos JOINs, essas linhas podem pertencer a operações diferentes. Isso poderia apresentar 2/2 prontos de forma enganosa. Correção: o servidor emite `EHL8_ROOM_STATE=players/slots,ready/slots,started,reserved/slots` em uma linha, sem PIN/saves. A UI usa o ÚLTIMO registro completo e só permite START quando `players=2, ready=2, started=0, reserved=0`. Registros parcialmente escritos, inconsistentes ou danificados falham fechados. Builds anteriores sem o marcador seguem o fallback com validação básica, sem alegação de segurança adicional.

**B. START persistente após a última reserva desaparecer.** A sala antiga podia ficar `in_game=True` até o loop de expiração, mas o log não emitia necessariamente `EHL8_ROOM_STARTED=0`. Correção: ao expirar/cancelar a última reserva sem jogadores ativos, servidor emite mudança de sessão e novo estado completo; o lobby pode ser reutilizado com controle do host.

**C. Integridade do arquivo de save entre a cópia e a substituição.** O `copy_atomic` já comparava origem e temporário byte-a-byte, porém a validação estrutural da cópia final era feita depois do commit. Correção: quando a operação destina-se a um `.sav` jogável, validar o temporário ANTES do rename. Para a cópia forense `.raw` de um arquivo inválido, preservá-lo byte-a-byte deliberadamente sem exigir que seja jogável. **Isto NÃO é verificação de checksum interno do setor.**

**D. Espera longa da sala sem START.** Teste novo com subprocesso do servidor Python EHL8 REAL + dois clientes TCP reais, HEARTBEAT a cada ~10s durante >30s, sala ainda não iniciada, seguido por START do host; não manipula .sav e não simula o gráfico do Emerald.

### Testes/regressões incorporados

- `tests/test_emerald_launcher.py`: snapshots atômicos; logs legados; snapshot parcial/contraditório; reservas.
- `tests/test_emerald_session_server.py`: log de estado sem PIN, liberação após reserva expirada ou expulsa.
- `tests/test_ehl8_launcher_manual_host.py`: soak >30 segundos com dois peers de socket, HEARTBEAT e START manual.
- `tests/test_save_profiles.c`: arquivo inválido de backup não pode substituir o atual.
- `tools/emerald_qa_lab.py`, engine SDL2, sprites, protocolo wire EHL8, saves originais e Android **não foram alterados nesta branch**.
- O `Auto QA` Windows+Linux e a compilação completa Windows do HEAD final precisam ser conferidos antes da promoção. Corrigir falhas apontadas; nunca declarar sucesso somente pelos testes anteriores.

## 3. Aceite da beta — etapas e evidências

| Gate | Teste real necessário | Resultado |
|---|---|---|
| START | QA_A e QA_B presos antes de START e liberados depois. | **Aprovado pelo usuário** na revisão base PR #23; confirmar ausência de regressão na nova build. |
| Movimento | Ambos veem sprite remoto no mesmo mapa e movimento bidirecional durante 2–5 min. | **Pendente** |
| Transição | Sair e voltar de mapa, reaparecimento, culling e sprite correto. | **Pendente** |
| Rede | Queda e reconexão dentro de 60 s, sem freeze/sprite fantasma e sem duplicar identidade. | **Pendente no jogo real** |
| Saves | Dois perfis de QA separados, gravação manual e reabertura offline válida. | **Pendente no jogo real** |
| Entre casas | Dois computadores na VPN privada com o mesmo ZIP, teste de firewall e IP. | **Pendente** |
| PvP/troca | Convite/aceite e commit seguro usando o Emerald existente. | **Não implementado no EHL8** |
| Android | APK ARM64 e crossplay Windows/Android real. | **Não comprovado** |
| Windows | Build completo + hashes + ZIP extraível de SHA exato. | **Verificar novo CI**, não confundir com QA de gameplay. |

### Como fazer o próximo teste em segurança

1. No Windows, preservar a pasta antiga. Baixar somente o ZIP da **revisão desta branch** depois de aprovado o build; extrair em pasta nova. Não colocar saves pessoais como QA_A/QA_B.
2. No QA Lab, iniciar servidor, entrar QA_A e QA_B, esperar START. Confirmar que os dois jogos abrem mas não aceitam controles antes de START. Conferir 0/2 → 1/2 → 2/2 e READY 2/2.
3. Esperar pelo menos 30 segundos **sem START**; verificar que a sala continua 2/2 e não começou sozinha.
4. Pressionar START, carregar cada save QA, levar ambos ao mesmo mapa e próximos dentro da câmera. Validar movimentos em ambas as direções.
5. Testar transição e retorno de mapa, simular queda de uma instância, observar reserva de slot/reentrada e, por fim, salvar/fechar/abrir offline os dois saves QA.
6. Anotar revisão exata, resultado e logs relevantes. **Não compartilhar PIN, dados pessoais nem saves em público.**

## 4. Pesquisa para o futuro, sem esconder limitações

- GitHub Docs — attestations: https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations . Comprova proveniência e integridade do artefato quando gerada e **verificada**, não ausência de bugs. Planejar para release depois de gate real, sem adicionar privilégios desnecessários aos builds internos.
- Tailscale — compartilhar servidor privado: https://tailscale.com/docs/use-cases/personal-or-at-home-use/share-private-game-server . Solução de acesso criptografado e restrito; testar com firewall e IP correto, sem port-forward público.
- Android NDK ABI: https://developer.android.com/ndk/guides/abis . ARMv7 ainda presente no projeto; não prometer ARM64 até remover/recompilar objetos incompatíveis e testar hardware.

**Estado em aberto:** este incremento fecha partes de confiabilidade e QA, **NÃO** implementa PvP/trocas em EHL8, checksums internos nem Android. Continuar nos próximos commits/PRs sob o mesmo escopo, preservando escolhas anteriores.
