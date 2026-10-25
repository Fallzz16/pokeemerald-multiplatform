# Grand World Native — laboratório isolado (P0/P1)

**Status:** experimental. This is NOT a Windows release, APK, or playable port.
The goal is to preserve Grand World M8, the grass-only rule and PT-BR while
auditing which native C/SDL2 platform services can be migrated.

## Source of truth

1. Pinned World checkout: `evilchinesefood/PKMN-World`,
   `15d3888b0d81322a04d3c71b0bce18948761ee44`.
2. Grand World patch pipeline (this repository), using the exact existing scripts
   and preserving their order, including six heroes, Gen4/Gen5 pilot, lean
   shadows, grass-only and PT-BR.
3. The old `src/platform/` folder is **diagnostic input**, not automatically
   copied over the much newer World engine. Most similarly named sources diverge.

## P0 — pinned source reproduction

With a **disposable, clean** World checkout and a local checkout of this branch:

```sh
python3 tools/grandworld_native/compose.py --world ../world --grandworld . --report native-plan.json
python3 tools/grandworld_native/compose.py --world ../world --grandworld . --apply --report native-compose.json
make -C ../world modern -j2
make -C ../world validate
```

The script refuses dirty World trees, wrong SHA or missing patches, and it exits
at the first failure. Never point it at original saves or a working checkout you
intend to preserve. The `--apply` action is **not** a no-op.

The GitHub Action `grandworld-native-experimental.yml` runs this process and
publishes only diagnostic reports, never ROM files. Before citing any result,
check the run on the exact PR SHA.

## P1 — diagnostic, not native gameplay

```sh
python3 tools/grandworld_native/probe.py --world ../world --grandworld . --output native-probe.json
```

The probe compiles four old portable C modules **against World headers** and
records missing symbols/API conflicts. It intentionally does not claim a linked
native executable, successful game boot, screenshots or Windows test. Next:
replace incompatible host interfaces one by one behind a portable API,
then build all World sources into a native 32-bit executable. Treat any pointer
width assumptions explicitly; do not promise 64-bit compatibility.

## Recursos nativos experimentais integrados

Os tres fluxos do laboratorio **ja existem**, mas **nao dentro do gameplay
World**: (1) instalar/habilitar pacotes, (2) resolver e exibir imagens PNG/BMP
de menus e seguidores na aplicacao SDL2, e (3) escolher e persistir cada
estilo na interface (F1, setas, F5).

O demo inclui oito poses (n/ne/e/se/s/sw/w/nw) para mostrar corpo olhando
na diagonal enquanto a posicao percorre apenas X/Y. Nao modifica a logica
da M8, seus saves nem o codigo do sistema de seguidores real.

**Guia detalhado em portugues:** [STYLE_LAB_PTBR.md](STYLE_LAB_PTBR.md).

**Windows:** baixe somente o artefato do job `windows-host-diagnostic`
aprovado no CI, extraia-o e abra `ABRIR_STYLE_LAB.bat`. O pacote demonstrativo
usa imagens originais. Nao e uma versao jogavel do Grand World.

## Plugin/Mod Pack API v1 (data only)

The native Style Lab already has ZIP validation, an install/enable/disable
CLI, a catalog of enabled assets, and menu/follower PNG/BMP lookup in the host.
These are **not** integrated into the World gameplay engine or its save format.
Tiles/audio are catalogable but not yet applied to World game scenes.

```sh
python3 tools/grandworld_native/modpacks.py my-pack.zip
python3 -m unittest discover -s tools/grandworld_native/tests -v
```

Pack ZIP layout:

```text
my-pack.zip
  manifest.json
  assets/sprites/pikachu.png
  assets/menus/blue.png
```

Manifest example (replace checksums with the SHA-256 of each asset):

```json
{
  "api": 1,
  "id": "my-art-pack",
  "version": "1.0.0",
  "assets": [
    {
      "id": "pokemon/pikachu/idle",
      "path": "assets/sprites/pikachu.png",
      "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    }
  ]
}
```

The verifier checks paths, type allowlist, duplicates, limits, ZIP bombs,
unlisted files and SHA-256. It rejects arbitrary Python/JS/DLL executable
plugins. Hashes detect corruption, **not licensing or trusted authorship**.
Future native runtime integration must be opt-in, require a versioned lookup
API, atomic resource switches, fallback assets and separate user settings.
It must never modify SaveBlocks for purely cosmetic changes.

## Build packs from asset folders

Resource contributors can create reproducible ZIP packs without editing a
manifest or calculating hashes manually:

```sh
# Example layout: my-theme/assets/sprites/example.png
python3 tools/grandworld_native/build_pack.py \
  --assets ./my-theme/assets \
  --id my-theme --version 1.0.0 \
  --output ./my-theme.zip
```

The builder refuses executable files, symlinked assets, collisions and
overwriting an existing ZIP, then verifies its own output using the same
validator used by the pack manager. This does not prove that asset authors
have distribution rights.

## Experimental pack management commands

After validating a `.zip`, developers can install and enable it in a
**dedicated mod directory**, which must be separate from all player saves:

```sh
python3 tools/grandworld_native/pack_manager.py --root ./test-modpacks install ./my-pack.zip
python3 tools/grandworld_native/pack_manager.py --root ./test-modpacks list
python3 tools/grandworld_native/pack_manager.py --root ./test-modpacks enable my-art-pack
python3 tools/grandworld_native/pack_manager.py --root ./test-modpacks disable my-art-pack
```

The manager refuses to replace an installed pack, leaves installed files intact
when disabled, and writes `enabled.json` atomically. Activation also regenerates
`runtime-assets.tsv`; the SDL2 **Style Lab** loads enabled menu/sprite resources.
The actual World gameplay resource loader is not ported or connected yet. This feature runs on the developer host, not the game menu, and
needs Python. All pack images/audio must have appropriate usage rights.

## Verified milestones and important run evidence

- P0 source composition and GBA reference/validator: confirmed on GitHub Actions
  [run 40180883072](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40180883072).
  This is a GBA baseline validation, not a native build.
- C/SDL2 host surface compiled and passed synthetic 240x160 image/input tests on
  Linux; Windows `gw_host_preview.exe` + `SDL2.dll` compiled in
  [run 40182024859](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40182024859).
  Neither contains a running Grand World engine.
- P1 remains blocked by save-block layout invariants and differing GBA hardware
  API definitions. The guarded disposable World header overlay and 32-bit probes
  are experiments; examine their latest CI before reporting progress.

## P0–P5 status matrix

| Milestone | Current status | Hard completion gate |
|---|---|---|
| P0 source composition | Reference GBA rebuild + validate passed in run 40180883072 | Patches + GBA baseline build + validate |
| P1 linked native World | **Not implemented** | Full World executable links for host |
| P2 title/menu SDL2 boot | **Not implemented** | Real window and reproducible captures |
| P3 regions and save | **Not implemented** | Real 3-region QA, save/Continue |
| P4 followers/audio/battle | **Not implemented** | In-game differential tests |
| P5 Windows distributable | **Not implemented** | Executable, dependencies, user QA |
| Plugin in-game runtime | **Not implemented** | Versioned runtime asset resolver |

## Safety and rollback

No merge into `main`, GBA M8 or PT-BR branches. Keep the experiment in
`experiment/grandworld-native-p0-p5-plugins-20261025`. Exit and delete a
disposable World checkout to roll back. Do not overwrite player `.sav` files.
Do not distribute commercial ROMs/assets without permission.
