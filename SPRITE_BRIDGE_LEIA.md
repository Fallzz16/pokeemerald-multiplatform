# Emerald Vanilla+ v0.7 — Sprite Bridge (prévia segura)

A nova ferramenta prepara/importa **sprites alternativos de Pokémon já existentes no Emerald (Gerações 1–3)** a partir dos repositórios de Platinum, HeartGold/SoulSilver e Ruby.

**Ela não adiciona espécies da 4ª geração ao jogo, não altera saves, não modifica gráficos sozinha e não vem com centenas de PNGs da Nintendo.** Os gráficos dos doadores são transferidos quando a pessoa os escolhe; sem acesso a internet, é possível apontar a pasta de uma cópia local dos arquivos.

## Como usar (Windows)

1. No código fonte candidato, execute `SPRITE_BRIDGE.bat --source platinum --species pikachu gardevoir` para verificar sem instalar.
2. Se a verificação aprovar, execute `SPRITE_BRIDGE.bat --source platinum --species pikachu gardevoir --apply`.
3. O programa guarda **os cinco arquivos originais por Pokémon** em `<pasta_do_projeto>_sprite_backups/<data-hora>/` (fora da pasta de código) antes de qualquer mudança. O `manifest.json` contém os hashes originais e os novos.
4. Para importar vários Pokémon de uma vez, liste seus nomes separados por espaço ou vírgula. Máximo de 50 por rodada para não bloquear por horas.
5. Depois da importação, rode o teste/compilação da ROM/port e confira os sprites. **Não substitua o jogo estável antes de validar.**

Outras fontes:

```bat
SPRITE_BRIDGE.bat --source heartgold --species pikachu --apply
SPRITE_BRIDGE.bat --source ruby --species ralts kirlia gardevoir --apply
```

Fonte offline: acrescente `--donor-root "C:\caminho\pokeplatinum"` apontando para a raiz do repositório doador extraído.

## Limites importantes

- PNG é convertido para **64 × 64 px, sem interpolação nem pixel redesenhado**. A ferramenta retira bordas transparentes e centraliza/ancora, mas **bloqueia** se o conteúdo visual real ultrapassa 64 × 64, em vez de reduzir e borrar a arte.
- Frente e verso precisam caber numa única paleta de até **15 cores opacas + transparência**. Caso contrário, o importador bloqueia; não aplica quantização automática destrutiva.
- `anim_front.png` recebe dois quadros idênticos à nova frente; **as animações DS não foram portadas**. É preciso criar quadros manualmente para animar.
- Os ícones de party/menu permanecem do Emerald. Formas especiais e Pokémon Gen4 são deliberadamente recusados.
- Paletas shiny são remapeadas quando o doador fornece paletas compatíveis; tons sem correspondência ficam normais. Confira visualmente.
- **Sprite Bridge exige Python 3 e Pillow só no momento de importar sprites**. O jogo não precisa disso para rodar.
- Não há compilação ou avaliação em execução nesta entrega; todos os scripts do jogo anterior foram preservados.

Foco da atualização: preparar o fluxo seguro e reutilizável para as próximas importações, sem obrigar a importar centenas de imagens nem implementar novas espécies de uma vez.
