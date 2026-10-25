# Grand World Native — Style Lab e extensoes (experimental)

**Esta build nao e o Grand World jogavel.** Ela e um aplicativo SDL2 nativo para
validar a estrutura de extensoes do futuro port da M8. Nao abre ROMs, mapas ou
saves da World; nao substitui a traducao nem o desenvolvimento da base GBA.

## O que ja funciona no laboratorio

- Menus F1 com configuracao de estilo de fundo e sprite acompanhante.
- Selecionar visual `classic` ou um pacote instalado e habilitado para cada categoria.
- Alternancia em tempo real, sem reiniciar o programa.
- Persistencia em `mods/style-settings.ini`, nunca no SaveBlock do Pokemon.
- Recarregar os mod packs habilitados com F5.
- PNG e BMP, inclusive transparencia para sprites; validacao pre-instalar.
- Ferramentas Python de instalar/ativar/desativar/listar e gerar indice.
- Empacotamento executavel Windows x64 + DLLs pela CI (sem ROM do jogo).

### Testar no Windows

1. Extrair o artefato `GrandWorld_Native_StyleLab_Windows_Experimental.zip`.
2. Abrir `ABRIR_STYLE_LAB.bat`, sem tirar `.dll` da mesma pasta dos `.exe`.
3. Abrir ajustes com F1, selecionar linha com setas cima/baixo e estilo com
   esquerda/direita. O demonstrativo vem com `gw-demo-style` e `classic`.
4. Pressionar F1 para fechar; mover o personagem de teste com as setas.
5. Pressionar F5 para atualizar os pacotes instalados.
6. Para instalar um ZIP de tema novo, arrastar o ZIP para `INSTALAR_PACK.bat`.
   Este ultimo passo exige Python 3 instalado no Windows.

O prototipo carrega um fundo de mapa representativo na categoria MENU e um pequeno
sprite original na categoria FOLLOWER. Essas sao imagens de teste, nao
um mapa, personagem ou menu real da Pokemon World.

### Criar seu proprio mod pack

Em uma pasta local:

```text
meu-tema/
  assets/
    menus/
      background.png
    sprites/
      follower.png
```

Execute a partir do repositorio:

```sh
python3 tools/grandworld_native/build_pack.py \
  --assets meu-tema/assets --id meu-tema --version 1.0.0 \
  --output meu-tema.zip
python3 tools/grandworld_native/pack_manager.py \
  --root mods install meu-tema.zip --enable
```

O manifesto v1 e produzido pelo builder com hashes SHA-256 e dois identificadores
logicos: `menus/background` e `sprites/follower`. O codigo C nao conhece o
nome do ZIP: resolve os IDs no arquivo `mods/runtime-assets.tsv`, produzido
pela ferramenta de instalacao. Pacotes desabilitados nao aparecem no catalogo.
Por enquanto o runtime visualiza apenas esses dois IDs; o indice ja suporta
outros IDs para tiles, audio e outras imagens quando a World nativa tiver hooks.

Outros IDs futuros poderiam incluir:
`sprites/pokemon/25/north_0`, `menus/bag/background`,
`audio/route101/theme`. **Esses exemplos nao estao integrados ao jogo.**

## Estrutura do plugin

- **ZIP versionado** com `manifest.json` e lista de arquivos.
- Suporta PNG/BMP em `assets/menus/`, `assets/sprites/`, `assets/tiles/`.
- WAV/OGG em `assets/audio/` podem ser indexados; a reproduçao pelo
  jogo nativo ainda nao existe.
- Nao aceita DLL, scripts, executaveis nem chamada de APIs arbitrarias.
- Tamanho total descompactado, quantidade, paths, repeticoes, symlinks e hashes
  sao verificados antes de instalar.
- Os IDs logicos permitem fallback para graficos classicos.
- Um plugin de dados nao deve modificar saves nem alteracoes de gameplay.
- Hash nao autentica o autor; nao fornece licencas de reutilizacao de sprites.

### Interface C reutilizavel

`gw_style_index.h` oferece:
- `gw_styles_load` para carregar o catalogo ativo;
- `gw_styles_find` para resolver `tipo+pack+id` a um arquivo;
- `gw_styles_options` e `gw_styles_option` para selecionar pacotes;
- `gw_styles_read_prefs` e `gw_styles_write_prefs` para configuracoes externas.

`gw_sdl_host.h` oferece `gw_host_read_image_argb` (PNG/BMP e alpha).
Esses modulos podem ser reutilizados no port World quando ele compilar.

## Evidencias e limites

Em 25/10/2026:
- Linux: compilacao C/SDL2, testes Python, demo instalado/habilitado e
  `gw_theme_lab --selftest` com recursos PNG aprovados no Actions.
- Windows x64: compilacao MSYS2/SDL2/SDL2_image, demo instalado/habilitado,
  o mesmo self-test e empacotamento com bibliotecas dependentes aprovados.
- Prova: [GitHub Actions 40185608815](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40185608815)
  (veja o status do job correspondente ao SHA especifico).
- Nao ha validacao manual de navegacao visual em maquina fisica, Android APK
  ou gameplay real de Kanto/Johto/Hoenn.

## Integracao real que ainda falta

1. Concluir P1: compilar a World M8/PT-BR inteira em C nativo com rotinas
   BIOS/DMA, VRAM e formato de save compativeis.
2. Conectar `gw_styles_find` aos carregadores reais de sprites de seguidores e
   menus da World, sem tocar nos registros GBA antigos.
3. Expor menu de preferencias no jogo, usar fallback classico e migracao
   de `style-settings.ini` sem escrever no SaveBlock2/3.
4. Aplicar a mesma API nos builds Android e testar em dispositivos reais.

Nao chamar P2-P5 concluido antes de boot jogavel, QA de regioes, batalha,
save/continue e executavel Windows do **jogo**.
