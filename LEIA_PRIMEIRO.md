# Emerald Hybrid v1.0 — Laboratório M0/M1 (FONTE PARA TESTES)

Esta **não é a v1.0 final**, e o pacote ainda **não é um executável Windows pré-compilado**. É a primeira entrega verificável de ferramentas de QA.

1. Obtenha o **Emerald EHL8 M2 Preview completo**, que contém `pokeemerald.exe`, `SDL2.dll`, `emerald_profilectl.exe` e `EmeraldSessionServer.exe`. Extraia em pasta nova, sem substituir a versão estável.
2. Extraia os arquivos deste ZIP **dentro da mesma pasta**, de forma que fique `tools/emerald_qa_lab.py` ao lado de uma subpasta `tests/` e que `pokeemerald.exe` fique na raiz.
3. Se você tem Python 3.12 ou 3.13 instalado, dê dois cliques em **ABRIR_LABORATORIO_PYTHON.bat**. O jogo e o servidor abrem sem CMD; o BAT pode aparecer momentaneamente.
4. Opcionalmente, para compilar `EmeraldQALab.exe` (sem precisar de Python na próxima execução), execute **COMPILAR_EXECUTAVEL_WINDOWS.bat** uma vez. Esse procedimento **requer Python instalado, internet para baixar PyInstaller e capacidade de executar ferramentas locais**; instala PyInstaller somente no ambiente virtual `.qa_builder` dentro dessa pasta, sem privilégios de administrador.
5. Na interface, selecione dois `.sav` para importar cópias ou deixe os campos vazios para criar novas aventuras. Use **EHL8 local** ou **Offline** e clique **ABRIR 2 JOGOS**.
6. Feche os dois jogos normalmente; examine `report.json`, logs e saves isolados no diretório que aparece na interface. **Limpar sessão** apaga apenas a sessão de QA escolhida e pede confirmação.

### Limitações e segurança

- Não é um cliente para 50 bots (marco M4), nem a v1.0 estável.
- Nunca copie o mesmo perfil ativo da versão estável diretamente por cima. Se importar, selecione apenas os arquivos originais `.sav`, que são tratados como fontes somente leitura pelo gerenciador nativo.
- **Não exponha a porta EHL8 na internet.** O Lab usa somente `127.0.0.1` e dois jogadores.
- Os sete testes de Python passaram localmente usando processos e gerenciador simulados. **Ainda não houve execução visual real no Windows** nem compilação PyInstaller Windows na sessão de desenvolvimento.
- O código está preparado em estrutura de diretórios para futuro commit no repositório. **Nenhuma branch, PR ou instalação do usuário foi alterada por este ZIP.**

## Atualização M1.1 — Testar 50 contas sem abrir 50 jogos

O botão **SIMULAR 50 CONTAS** verifica clientes de protocolo EHL8 em 25 pares sequenciais. São bots de rede, sem arquivos `.sav`, sem gráficos e sem conexão externa. O teste gera `bots-report.json` com status e métricas aproximadas. **Ainda NÃO equivale a 50 jogadores simultâneos ou 50 contas reais completas.**

Ao compilar via `COMPILAR_EXECUTAVEL_WINDOWS.bat`, mantenha ambos os executáveis **EmeraldQALab.exe** e **EmeraldQABots.exe** na pasta do jogo. O botão não necessita de Python se os dois já estiverem compilados. Para mais detalhes, consulte `docs/V100_M0_M1_QA_LAB.md`.
