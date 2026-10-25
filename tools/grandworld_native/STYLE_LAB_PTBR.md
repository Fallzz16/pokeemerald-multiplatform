# Grand World Native — Style Lab e pacotes de recursos

> **Importante:** esta e uma ferramenta nativa de teste, **nao o jogo Grand World
> completo**. Nao roda mapas de Kanto, Johto ou Hoenn; nenhuma etapa P1–P5 da
> migracao da engine World esta marcada como concluida.

## O que ja funciona

- Aplicativo C/SDL2 com janela nativa para Windows, escala 240x160, teclado.
- Tela de configuracoes F1: estilos de **MENU** e de **FOLLOWER** independentes.
- Leitura de PNG/BMP externos com SDL2_image; opcao **CLASSIC** como fallback.
- Preferencias gravadas em `mods/style-settings.ini`, nao em arquivos `.sav`.
- Pacotes ZIP de recursos dados (sem executaveis), com versao de API,
  hashes SHA-256 e verificacoes de caminhos/perigo de ZIP bomb.
- Instalacao, listagem, ativacao e desativacao de pacotes via Python.
- Catalogo `mods/runtime-assets.tsv` gerado apenas com pacotes habilitados.
- F5 no aplicativo para recarregar os estilos habilitados.
- Biblioteca de poses visuais N/NE/E/SE/S/SW/W/NW independente do grid:
  o pequeno seguidor do **laboratorio** move-se so nos eixos X/Y, mas pode
  olhar diagonalmente para a posicao do jogador.
- Testes automatizados C/Python em Linux e Windows. Eles validam o laboratorio;
  **nao** comprovam gameplay da World.

## Como testar no Windows

1. Na pagina do PR #78, abra a compilacao mais recente com job
   `windows-host-diagnostic` **verde**.
2. Baixe o artefato chamado
   `grandworld-native-sdl2-host-windows-diagnostic-NOT-GAME`.
3. Extraia **todos** os arquivos juntos. A pasta inclui as DLLs.
4. Abra `ABRIR_STYLE_LAB.bat` ou `gw_theme_lab.exe`.
5. Use **F1** para trocar entre temas, **setas** para mover/escolher e
   **F5** para recarregar depois de ativar/desativar um pacote.
6. O pacote original `gw-demo-style` vem com fundo + seguidor demonstrativos
   (criaturas e imagens originais, sem graficos de terceiros).
7. Opcionalmente, arraste outro ZIP validado em `INSTALAR_PACK.bat`; esta
   operacao requer Python 3.12+ no Windows.

> Arquivos executaveis, DLL, scripts e bibliotecas carregaveis nao sao
> permitidos como plugins. Os pacotes se limitam a imagens/som. WAV/OGG e
> tiles sao catalogados, mas ainda nao mudam o gameplay nem o audio real.

## Criar um pacote novo

Estrutura da pasta:
```text
meu-pacote/
  assets/
    menus/
      background.png
    sprites/
      follower.png
      follower/
        n.png
        ne.png
        e.png
        se.png
        s.png
        sw.png
        w.png
        nw.png
```

Cada imagem do seguidor pode ter tamanho diferente, mas o laboratorio atual
redimensiona para 24x24 com amostragem nearest-neighbor. O fundo e exibido
em 240x160. O arquivo follower.png e a imagem de seguranca se alguma
orientacao opcional estiver ausente.

Para empacotar e instalar, na raiz do repositorio:
```sh
python tools/grandworld_native/build_pack.py --assets meu-pacote/assets --id meu-pacote --version 1.0.0 --output meu-pacote.zip
python tools/grandworld_native/pack_manager.py --root mods install meu-pacote.zip --enable
python tools/grandworld_native/pack_manager.py --root mods list
```

Se o Style Lab estiver aberto, aperte **F5**. A selecao de MENU e FOLLOWER
e separada: um pacote pode mudar apenas uma das categorias.

### Pacotes e API

- `manifest.json` declara `api: 1`, `id`, `version` e `assets`.
- Identificadores conhecidos: `menus/background`,
  `sprites/follower`, `sprites/follower/n` ... `/nw`.
- Os arquivos ficam em `assets/menus/`, `assets/sprites/`,
  `assets/tiles/` ou `assets/audio/`.
- Formatos aceitos pelo validador: PNG/BMP; WAV/OGG.
- O catalogo so publica arquivos que continuam correspondendo aos SHA-256.
- O gerenciador nao escreve saves, nao executa codigo do ZIP e nao substitui
  silenciosamente um pacote existente.
- Um SHA-256 nao significa que o recurso seja licenciado para distribuicao.

## Proximas etapas da integracao com o jogo

Quando P1 (World nativa linkada) for atingido, integrar o resolvedor ao carregador
real de texturas do mapa e as interfaces da World. Somente apos testes reais de
batalhas, seguidores, saves e regioes poderemos anunciar P2–P5. O seguidor
do laboratorio e uma prova de conceito, **nao o seguidor da M8**.

Repositorio: https://github.com/Fallzz16/pokeemerald-multiplatform/pull/78
