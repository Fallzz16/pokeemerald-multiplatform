# Grand World M8 — Expansion compatibility gate

Source: user-supplied `pokeemerald-expansion-master.zip`. Never upload the ZIP, game ROMs or graphics to this repository without rights review.

## Verified from ZIP structure (not tested on GBA)
- All 43 M8 pilot family representatives have `anim_front.png`, `back.png`, `icon.png`, and `normal.pal` in `graphics/pokemon/<name>/`.
- Expansion source files exist for `src/debug.c`, `src/pokemon_summary_screen.c`, `src/map_name_popup.c`, `src/follower_npc.c` and `src/pokedex_plus_hgss.c`.
- `include/config/summary_screen.h` has IV/EV views disabled by default.
- `include/config/follower_npc.h` has NPC followers disabled; the documentation says enabling them increases SaveBlock3 size. NPC followers are not equivalent to fully working Pokémon followers.
- Source ZIP lacks Git history; it is unsuitable for an automatic merge-base strategy.

## Compatibility decisions
| Target | Decision | Required gates |
| --- | --- | --- |
| Test tooling | Read-only inventory now | Run new audit in CI, independent reproducible tests; no release-criteria promotions |
| 43 family sprites | Metadata inventory only | Check entire evolution/form trees, palettes, licensing/credits, mapping to World species and ROM space |
| Summary improvements | Defer gameplay port | Verify layout/task dependencies, data structures, offsets, graphical resources and save/reload |
| Map-name popups | Defer gameplay port | Audit World map IDs, Kanto/Johto/Hoenn naming, transitions, VRAM/palette use |
| Followers | Do not enable yet | SaveBlock3 compatibility/migration proof, map object slots, route transfers, sprite alignment, movement and reload |
| HGSS Pokédex | Do not enable yet | Species-index migration, caught/seen bit arrays, regional filtering, save and dex list tests |

## M8 invariants
- The existing PR #68 branch and PR #69 remain untouched by this exploration.
- Do not copy wholesale `src/`, `include/`, `data/`, or `graphics/`.
- Keep all existing regional-gate/save regressions and the 105 acceptance criteria.
- Do not certify a criterion from ZIP inspection alone.
- Before importing assets or code, check upstream credits and rights; preserve attributions.
- Do not redistribute copyrighted game content or game ROMs.

## Reproduction

```bash
python3 tools/grandworld/audit_expansion_zip.py /path/to/pokeemerald-expansion-master.zip --output expansion-audit.json
```

This command reads only the user-provided ZIP, creates a JSON report, and does not modify the ROM, source checkout or saves.
