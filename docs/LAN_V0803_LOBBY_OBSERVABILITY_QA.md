# Emerald Hybrid Multiplayer — v0.8.3 EHL8 Lobby Status / QA

**Atualização incremental e experimental do PR #10.** Esta branch é `feature/lan-v0803-ehl8-lobby-observability`, PR #11. Base: `feature/lan-v0803-dedicated-session-core`. Não alterar o jogo original já instalado.

## Por que esta atualização existe

O launcher da base dizia apenas "Servidor EHL8 ativo", conferindo se o processo `EmeraldSessionServer.exe` ainda estava rodando. Isso **não comprova** um lobby disponível, jogadores conectados, prontidão nem se o jogo pode realmente começar.

## Adicionado / modificado (efetivamente)

- `tools/emerald_session_server.py`: opção **`--status-file <caminho-local>`**, desativada por padrão para compatibilidade. O processo grava JSON schema 1 atomicamente (`arquivo.tmp` + `os.replace`), no início, nas entradas, transições Ready/Start, saídas e fechamento normal. Campos: `schema`, `phase` (`lobby`/`playing`/`stopped`), `slots` (máximo 2), `players` (IDs locais e indicador Ready). **Não inclui PIN, IP, nickname de conta on-line ou dados do save**. Erros opcionais de escrita não derrubam o jogo/servidor.
- `tools/emerald_launcher.py`: inicializa servidor com status file privado sob `logs/` e nome aleatório por sessão; lê JSON a cada 1,3 s com limite de 8192 bytes e validação estrita de `schema`/fase/slots/IDs/Ready; mostra **quantos dos dois jogadores realmente conectaram**, IDs locais prontos e fase. Se status não existe, informa que o servidor está iniciando, em vez de alegar lobby funcional.
- `tests/test_emerald_session_server.py`: teste TCP real de entrada, confirmação Ready, entrada do segundo peer, Start, saída e publicação sem PIN.
- `tests/test_emerald_launcher.py`: testes contra JSON malformado, arquivo ausente, entrada muito longa, profile ID e slot inválidos.
- `.github/workflows/test-v0803-dedicated-server.yml`, `.github/workflows/build-v080-graphical-launcher.yml`: CI Linux/Windows na branch experimental.

**Não alterado:** `src/link.c`, `src/platform/sdl2.c`, renderizador, código do cliente EHL8 C, SDL2, Android, dados ROM, sprites, mapas, Cable Club, quests e formato de save. **Removido: nada.**

## QA e matriz de aceitação

### Automatizado
- [x] Teste de sintaxe e lógica do servidor (Linux).
- [x] Integração C nativa `lnet_session_client.c` ↔ servidor Python em TCP loopback (Linux).
- [x] GUI testa leitura defensiva de JSON do lobby no Windows; **conferir run exato abaixo**.
- [ ] Verificar **conclusões finais** de PyInstaller Windows (server e launcher).
- [ ] Conferir CRC/PE e conteúdo do pacote resultante.

### Pendente em duas instâncias reais do Emerald
- [ ] Windows host com `EmeraldSessionServer.exe`, dois clientes Windows com contas locais e saves reais em pastas/perfis diferentes.
- [ ] Ambos conectam com o PIN correto, entram na própria campanha e aparecem no mesmo mapa.
- [ ] Testar movimento, warp, retorno ao mapa, culling fora da câmera, 15–30 min sem travamento e perda de conexão.
- [ ] Fazer save individual e reabrir depois que servidor/jogo fechar, sem misturar progresso.
- [ ] Verificar que login inválido, jogador repetido e servidor desligado exibem comportamento recuperável.
- [ ] **Trocas/batalhas pelo dedicado ainda não existem**: elas continuam na ligação P2P Cable Club. Não simular nem prometer.

### Diagnóstico
- Painel mostra `Lobby EHL8 · 1/2 jogadores · profile_X ✓` somente quando há confirmação no status-file local. `✓` significa Ready no servidor, **não** prova progresso da ROM.
- `logs/cliente-ehl8.log` tem transições de estado do cliente nativo sem PIN ou conteúdos do save.
- Quando for relatar problemas, omitir dados pessoais e IPs privados de logs.
- Se houver erro na montagem do pacote ou CI, interromper a distribuição: não usar binário avulso nem alegar sucesso parcial como jogo pronto.

## Segurança e rollback

Servidor dedicado é para LAN privada ou VPN privada. PIN de seis dígitos **não substitui autenticação real de internet**; nunca encaminhar portas 45680/45681 à internet pública. A configuração de rede usa `0.0.0.0` ao hospedar, portanto conferir manualmente as regras do firewall para permitir somente peers confiáveis.

O arquivo de status é **diagnóstico local**, não uma API de autoridade nem um canal de comando. Seus dados podem ser modificados por outros processos com acesso ao diretório; apenas exibir campos validados.

**Base segura conhecida:** usuário confirmou instalador v0.8.2 funcionando; para voltar, use aquela instalação existente e não exclua profiles. Baseline de gameplay LAN anterior: `feature/lan-v0721-viewport-culling`, SHA `a87e2c49e453db32def5e71ba2a2e696a911d504`. PR #11 deve permanecer draft até QA de gameplay.

## Continuidade de trabalho

Ler `AI_README.md` (decisões 1–116, histórico completo), `AGENTS.md`, `docs/LAN_V0803_DEDICATED_SESSION_CORE.md`. Não confundir integração de rede nativa/testes C com gameplay real aprovado. Em cada novo incremento: código adicionado/modificado/removido, testes verificados com URL/commit, risco, rollback, funções incompletas.
