# Pokémon Emerald Hybrid — M3.2: estado da sala no jogo real
**Data:** 2026-10-21. **Branch:** `feature/emerald-m32-room-presence-20261021`. **Base:** PR #36, commit `133322b84df0bfe24d728c9a23f0fac0f82ef07c`.

## Motivação comprovada na auditoria
O servidor EHL8 já enviava `PLAYER_LIST` com jogadores conectados, `READY` e identidades de perfil. Entretanto, `src/lnet/lnet_session_client.c` simplesmente ignorava essa mensagem. A janela real do Emerald mostrava texto genérico, sem distinguir 0/2, 1/2, 2/2 e prontos. Isto gerava uma diferença entre a sala do launcher e o que o convidado via dentro do jogo.

**Escopo:** APENAS multiplayer do Emerald original. Sem mudanças em mapas, Pokémon, campanha, saves, formato da rede ou Cable Club P2P. QA Lab continua uma ferramenta SEPARADA do launcher do usuário final.

## Implementado nesta branch
1. **Novo `src/lnet/lnet_room_roster.h`:** parser puro C para o pacote EHL8 `PLAYER_LIST` JÁ EXISTENTE (count, slot, ready, len, profile). Rejeita registros truncados, duplicados, inválidos, IDs com caracteres proibidos, comprimentos errados, flags READY > 1, slots fora de 1..2 e bytes extras. Não grava perfis/nomes em save ou disco.
2. **`src/lnet/lnet_session_client.c/.h`:** recebe e valida a lista, guarda somente os totais `players` e `ready` em memória, e expõe `lnet_session_client_get_roster`. Ao perder a conexão, invalida a lista em cache. Um pacote de lista malformado é tratado como violação de protocolo — a UI nunca deve exibir ocupação inventada.
3. **`src/link.c`:** `PortLanDedicatedRoomSnapshot()` disponibiliza os totais em formato compacto, somente na thread do jogo. Não acessa sprites/saves nem altera sincronização do mapa.
4. **`src/platform/sdl2.c`:** transfere o snapshot do jogo ao renderizador em `SDL_atomic_t`, sem concorrência sobre ponteiros do socket. O painel de espera recebe a atualização sem pausar VBlank ou heartbeat; overlay não aparece em offline/P2P nem após START.
5. **`src/lnet/lnet_wait_overlay.h`:** pequena fonte bitmap foi estendida com algarismos, mostrando `JOGADORES 1 DE 2` e `PRONTOS 1 DE 2` enquanto a sala aguarda. Ocupação desconhecida não gera números falsos; cabe no viewport 240×160. Não modifica gráficos originais do Pokémon.
6. **`scripts/verify_v080_profile_patch.py`:** permite remover precisamente as 5 novas inserções/revisões SDL2 antes da comparação estrita do hash original, sem desligar a auditoria de integridade.
7. **Testes:** `tests/test_ehl8_room_roster.c` (NOVO) cobre listas boas e malformadas e integridade dos totais; `tests/test_ehl8_wait_overlay.c` amplia o teste dos pixels do painel; `tests/native_ehl8_client.c` e `tests/test_ehl8_native_bridge.py` adicionam prova E2E de dois clientes C + servidor Python REAL gerando `PLAYER_LIST=2/2,READY=2/2` e poses remotas recebidas.
8. **CI:** Auto QA e Windows Full Preview agora observam branch `feature/emerald-m32-*`; compila e executa o teste C do parser no Linux.

**Arquivos removidos:** nenhum. **Não modificados:** `tools/emerald_launcher.py`, `tools/emerald_session_server.py`, QA Lab, formato de saves, protocolo wire EHL8, menus do GBA, Cable Club, Android. Nenhum `.sav` foi copiado/importado ou alterado para implementar a sala.

## Testes e critérios de aceite

### Automáticos
- Compilar parser de roster e testes de overlay com `gcc -std=c99 -Wall -Wextra -Werror -O2`.
- Executar `python -m unittest discover -s tests -p test_ehl8_native_bridge.py -v` no Linux: C real deve aceitar o snapshot autenticado e mostrar 2/2 READY.
- Auto QA Windows/Linux e Windows Complete Preview precisam concluir no SHA FINAL (jobs game/gui-tools/portable). O ZIP deve verificar extração, hashes do par EHL8 e detecção de incompatibilidade. Registros de executáveis de SHAs anteriores NÃO certificam este incremento.
- CI legado GBA `Compare` pode permanecer falho; **não** classificar como verde universalmente.

### Prova visual do usuário (ainda NÃO executada)
1. Baixe somente o ZIP do run completo desta revisão final, extraia em nova pasta sem substituir os saves pessoais. Use perfis de teste.
2. Abra **EmeraldLauncher.exe**, não o QA Lab: crie sala (jogo do host abre, launcher fica disponível).
3. Verifique painel no host: inicialmente `JOGADORES 1 DE 2`, `PRONTOS 1 DE 2` após JOIN/READY. Em outra instalação, entre com IP LAN/VPN e PIN.
4. Ambos precisam mostrar `JOGADORES 2 DE 2`, `PRONTOS 2 DE 2`. Espere sem START; continua 2/2 estável, controles bloqueados.
5. Host clica `INICIAR PARTIDA`; os contadores da sala desaparecem, os controles liberam; abrir saves e aproximar treinadores no mesmo mapa.
6. Checar sprite remoto dos dois lados, mapa/transições, visual de desconexão, reconexão real e integridade do save reaberto offline.
7. Abra offline e Cable Club antigo em testes separados; nenhum HUD EHL8 deve aparecer. Se der erro, coletar logs de servidor/game e screenshots, sem incluir PIN ou dados privados.

## Segurança e riscos
- O snapshot contém SOMENTE contagens na UI. Identificadores presentes no protocolo original são validados e descartados pelo parser; não aparecem na tela nem em logs novos.
- O EHL8 existente usa PIN LAN e NÃO deve ser exposto à Internet pública. Para teste entre casas use VPN privada e firewall adequado.
- Um servidor compatível que envie `PLAYER_LIST` inválida causará desconexão segura, por design. Limitações de 2 jogadores são explícitas nesta fase.
- Mesmo com testes verdes, não representa prova de movimento gráfico em duas máquinas, batalhas e trocas EHL8, segurança WAN, Android ARM64 nem checksums internos por setor.
- **Rollback:** PR #36 SHA `133322b84df0bfe24d728c9a23f0fac0f82ef07c`, ZIP já verificado, sempre em pasta separada. Não mesclar automaticamente esta branch nem modificar `main`.

## Continuação sugerida
A próxima camada de jogabilidade requer teste humano com dois personagens e, depois, convite/aceite de batalhas/trocas da engine Emerald. Não iniciar transações de Pokémon enquanto não existir rollback seguro e integridade setorial validada.
