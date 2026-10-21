# Kanto V0.10 — pontos de reaparecimento independentes

## Objetivo
Permitir que uma derrota em Kanto retorne ao último Centro Pokémon **de Kanto**, sem apagar o Centro Pokémon anterior de Hoenn, preservando a viagem de volta pelo barco e o formato existente de saves.

## Implementação
- `VAR_KANTO_LAST_HEAL_LOCATION` usa **uma única variável persistente anteriormente livre** do save (`VAR_UNUSED_0x40F7`), sem aumentar o tamanho dos blocos nem mudar outros números de variável.
- Os Centros de Vermilion, Viridian, Pewter, Cerulean, Lavender, Celadon, Fuchsia, Cinnabar e Saffron registram seu índice próprio ao serem acessados pelo script `MAP_SCRIPT_ON_TRANSITION`.
- `DoWhiteOut` continua com todas as operações originais de perda de dinheiro, cura da equipe e reset do estado. **Somente se o mapa atual pertence ao grupo Kanto**, aponta o destino para o lobby do Centro registrado. Em Hoenn continua usando `SetWarpDestinationToLastHealLocation` como antes.
- Fallback para Centro Pokémon de Vermilion quando a variável está zerada, contém valor inválido ou veio de um save anterior.
- A viagem Kanto → Hoenn continua usando o último local de cura de Hoenn, pela função existente `Kanto_ReturnToHoennHealWarp`.
- Os mapas anteriores 0–83, cinco treinadores, 42 itens e índices de flags não mudam.

## Testes
`.github/workflows/kanto-v10-regional-respawn.yml`: verifica script/mapa dos nove Centros, os nove índices, tabela C do whiteout, preservação do caminho de Hoenn, e o tile de respawn não bloqueado da geometria de FireRed, além do build Windows.

## Limitações e QA obrigatório
Estes são os locais de **whiteout**, não uma implementação completa de Fly ou rede. É necessário abrir o jogo e verificar com saves descartáveis: visitar dois Centros diferentes de Kanto, perder uma batalha, reaparecer no Centro correto, recarregar um save feito em Kanto, voltar no barco e verificar o Centro anterior de Hoenn. Também testar saves antigos sem variável inicializada, e regressões Windows/Android e LAN. Não mesclar com a branch principal sem QA real.
