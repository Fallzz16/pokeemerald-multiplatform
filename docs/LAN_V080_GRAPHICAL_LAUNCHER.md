# Emerald Hybrid v0.8 — Launcher gráfico Windows (candidato experimental)

> **Importante:** este é o início do launcher solicitado, não a v0.8 completa. Não existe ainda servidor dedicado nem lobby de 4 jogadores. O botão dedicado aparece indisponível, sem falsa simulação.

## O que funciona

- `EmeraldLauncher.exe`: janela Windows própria (Tkinter empacotado em EXE sem precisar instalar Python), tema verde-esmeralda, seleção de **conta local** (perfil).
- Criar um save novo ou importar **cópia** de `.sav` Emerald existente via `emerald_profilectl.exe`. O launcher não escreve nos dados internos de Pokémon, mantém o Trainer ID e salva um apelido separado em `profile.json`.
- Selecionar perfil e escolher **Jogar offline**, **Hospedar e jogar** (host P2P para 2), **Jogar com amigos** (cliente por IPv4 e porta; aceita VPN privada).
- Ao iniciar, repassa `--profile-root` e `--profile-id` à versão v0.8 M1 do `pokeemerald.exe` para isolar saves, sem alterar o jogo original nem a interface GBA.
- Validação de IPv4, porta 1..65534 e perfil antes de iniciar. Os dois canais TCP são `porta` e `porta+1`.

## O que ainda NÃO funciona

- **Servidor dedicado** que hospeda sem jogar, painel administrativo/lobby, autenticação pela internet, até 4 jogadores, nome sobre sprites, QR, descoberta automática LAN, chat, atualização automática, painel rápido no jogo.
- Conta online com e-mail/senha: **não** existe. A opção #81A aprovada pelo usuário exige LAN sem conta obrigatória. Neste primeiro launcher, **conta** significa seleção de perfil local com save independente. Caso ele prefira login online opcional, obter aprovação antes de implementar.
- O APK Android permanece com a tela LAN anterior. A UI gráfica deste PR é **Windows apenas**; Android receberá experiência equivalente em uma etapa posterior, sem fingir que já está pronta.
- A ferramenta `sp_validate_file` usada no importador verifica **somente estrutura**, sem validar todos os checksums. Backup automático após cada save manual ainda precisa de integração. Não use o único arquivo de save original.

## Como testar sem tocar na instalação aprovada

1. Extraia o pacote Windows candidato **em pasta nova**, separado das versões v0.7.2.1 e v0.7.2.2.
2. Confira que `EmeraldLauncher.exe`, `pokeemerald.exe`, `SDL2.dll` e `emerald_profilectl.exe` estão lado a lado.
3. Abra `EmeraldLauncher.exe`, clique **Criar ou importar conta** e escolha apelido. Para importar, escolha uma **cópia** de seu arquivo .sav.
4. Selecione o perfil na coluna esquerda e pressione **Jogar offline**; salve no jogo, feche, reabra e confira progresso.
5. Para **Hospedar e jogar**, selecione perfil e porta 45680; outro PC entra via **Jogar com amigos**, usando IP LAN/VPN privado do host. Use outro perfil no PC do amigo, sem reutilizar seu save.
6. Teste sair do mapa, entrar novamente, sprites e Cable Club. O mundo multiplayer **continua experimental** e requer validação de save em duas instâncias.
7. Faça backup de qualquer .sav antes de testar. Não abra o mesmo perfil em dois processos.

## Armazenamento

Por padrão os perfis ficam em `%LOCALAPPDATA%\EmeraldHybrid\profiles\<id>\pokeemerald.sav`. O apelido é salvo em `profile.json`, sem modificar o .sav.

**Modo portátil:** crie um arquivo vazio chamado `PORTABLE_MODE.txt` na pasta do `EmeraldLauncher.exe` **antes** de criar o primeiro perfil. Os perfis passarão a ficar em `<pasta do jogo>\profiles`. O launcher não move automaticamente arquivos existentes de uma modalidade para outra. Faça backup antes de trocar.

## Testes técnicos

- `python tools/emerald_launcher.py --self-test`
- `python -m unittest discover -s tests -p test_emerald_launcher.py -v`
- `python -m PyInstaller --onefile --windowed --name EmeraldLauncher tools/emerald_launcher.py`
- O workflow de Windows usa `python 3.12` + PyInstaller, e publica `EmeraldLauncher.exe` apenas após os testes. Rodar na branch/revisão **exata** e conferir logs no GitHub Actions.
- Este launcher é só frontend. O executável do jogo é o candidato M1 da branch v0.8; testes nativos anteriores da versão M1 não significam que todo o novo launcher esteja validado em gameplay.

## Continuidade para outras IAs

Consultar `AGENTS.md`, `AI_README.md`, `docs/LAN_V080_ARCHITECTURE.md` e esta página **antes de editar**. A base de rollback para gameplay é `feature/lan-v0721-viewport-culling` commit `a87e2c49e453db32def5e71ba2a2e696a911d504`. A branch de launcher se baseia em `feature/lan-v080-m0-m1-foundation`, não substitui seus módulos. Toda atualização deve registrar adicionados, modificados, removidos, testes, riscos, lacunas, SHA e como retomar.
