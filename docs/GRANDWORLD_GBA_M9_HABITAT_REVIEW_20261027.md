# Grand World GBA M9 — Habitat quality gate (27 Oct 2026)

> Review of proposals only, **not** 16 patches, not a ROM modification, and not a gameplay acceptance. Keep M8 stable and unmerged.

## Evidence consulted

- Original 36 missing terrestrial table species: [auditor #84, run 40300985431](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40300985431); original wild JSON SHA256 `c6eb187450227f0bccc40241f7f7820f4a8cbf7574dcaab17141bdba86bb01d3`.
- 16 grass-tile-gated same-route candidates: [#87, run 40313368346](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40313368346), artifact `candidate-route-additions.json`; Route 111 rejected (zero observed grass).
- Existing original-land evolution roots for Dragonair, Forretress and Pelipper: [#90, run 40316082335](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40316082335).
- [#89 mGBA Qwilfish 8/8](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40316499670) establishes a **single experimental natural spawn**, not biome quality or production approval.

## Decision buckets, mutually exclusive

- **9 aquatic-first proposals:** hold pending fishing/surf/water-access decision; a technical grass spawn alone is poor justification for putting aquatic species in tall grass.
- **3 evolution-linked proposals:** original land-parent path already declared; avoid extra direct route slots until evolution and source-parent capture are certified.
- **4 riparian/shoreline proposals:** possible *design candidates only* if a real walkable grass zone is appropriately adjacent to water, local level curve is right, and regular progress can reach it.

All **16** remain **ON HOLD**. These are subjective habitat recommendations grounded in species ecology, **not** verification of map water placement, real player reachability, exact probability by slot, source feature flags, capture, or release suitability. They must not be automatically applied.

| Species | Provisional map | Slot | Original source | Review bucket | Reason / next acceptance gate |
|---|---|---:|---|---|---|
| Barboach | Route 114 | 3 | Fishing | Aquatic-first | Water-dependent: preserve fishing or design a specifically wet bank habitat |
| Buizel | Route 30 | 11 | Surf/water | Riparian candidate | Can be considered near accessible streams, but map geography and level curve need play review |
| Carvanha | Route 118 | 10 | Fishing | Aquatic-first | Fast predatory fish: prefer traditional fishing or surf availability |
| Chinchou | Route 47 | 10 | Fishing | Aquatic-first | Deep-water ecology: inappropriate to add to generic tall grass |
| Corphish | Route 102 | 10 | Fishing | Riparian candidate | Shallow-water marsh adjacency might work with purpose-designed grass |
| Dragonair | Route 45 | 11 | Fishing | Evolution already linked | Dratini is on original land tables; confirm live evolution before direct route slot |
| Forretress | Route 28 | 11 | Rock Smash | Evolution already linked | Pineco original terrestrial lineage exists; avoid extra land encounter without need |
| Goldeen | Route 42 | 11 | Surf/water | Aquatic-first | Fish species better obtained by traditional water mechanics |
| Magikarp | Route 103 | 11 | Fishing | Aquatic-first | A fish in ordinary tall grass harms habitat coherence |
| Pelipper | Route 104 | 11 | Surf/water | Evolution already linked | Wingull original terrestrial lineage exists; coast habitat possible but redundant |
| Poliwag | Route 35 | 9 | Fishing | Riparian candidate | Possible at ponds/riverbanks if accessible tall grass and compatible progression |
| Poliwhirl | Route 44 | 11 | Surf/water | Riparian candidate | Possible by water or Poliwag lineage; compare both before new slot |
| Qwilfish | Route 32 | 5 | Fishing | Aquatic-first | Real spawn 8/8 proved technical case, NOT suitable grass habitat |
| Staryu | Route 34 | 7 | Fishing | Aquatic-first | Marine species should remain water-associated unless a special shoreline explanation |
| Tentacool | Route 115 | 10 | Surf/water | Aquatic-first | Do not put marine jellyfish into ordinary inland tall grass |
| Wailmer | Route 121 | 10 | Fishing | Aquatic-first | Large aquatic whale: prioritise surfing/fishing or events instead of grass |

## Release decision

1. Do not merge the 16 provisional table edits into the stable M8/PT-BR game; no original encounter or story maps have been changed by this review.
2. Keep original aquatic encounter behavior conceptually separate from the grass-only *overworld visibility* policy. **Walking grass encounters without roaming sprites does not logically require removing Surf/Fishing/Rock Smash encounters.** Decide whether the user's intended limitation is 'no roaming overworld wild Pokémon' versus an actual ban on all water/fishing encounters. This can preserve game authenticity and avoid most contrived grass placements without breaking save/IDs. No mechanical policy changes should be made until this is clarified and tested in a separate branch.
3. For the 3 already-evolution-linked proposals, prioritize real evolution/campaign access tests first.
4. For 4 riparian candidates, verify mapped water/grassy adjacency, passable route from ordinary entrance, wild levels and reasonable odds, then catch from natural grass on a real ephemeral ARM ROM.
5. For the remaining 9 aquatic species, investigate existing ordinary aquatic encounters, scripted gifts, trades and alternative non-grass methods before touching land tables.

## Latest unrelated proof gates (not rerun)

- [PR #95, run 40465755959](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40465755959): actual NPC trade Bagon -> Horsea **12/12 mGBA** using debug-Bagon fixture.
- [PR #96, run 40466888877](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40466888877): actual original Silph Lapras gift **12/12 mGBA**, debug map warp as setup.
- [PR #97](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/97): Horsea -> Seadra level-32 original evolution, newly submitted; require focused CI PASS evidence before labeling it validated.

**No physical GBA cartridge, production release, full Pokédex completion, story reachability or save compatibility regression was newly certified by this note.**


## Source-verified grass-only policy caveat (27 Oct 2026)

The actual repository script `tools/grandworld/apply_grass_only.py` inserts a guard into `src/wild_encounter.c` so `GW_GRASS_ONLY_WILD` allows non-scripted stepping encounters **only** on metatile behaviors `MetatileBehavior_IsPokeGrass` and `MetatileBehavior_IsAshGrass`. It also makes standard Fishing and Rock Smash encounters return early. This is a confirmed **source-code rule**, not a claim that all map behaviors were already surveyed.

**Implication:** source-defined `land_mons` in caves may be unreachable under the current grass-only policy even when the land table and wild encounter rate are valid. A newly identified example is Bagon in original `MAP_METEOR_FALLS_B1F_2R` land slots 2/4/6. If all walkable floor tiles there are non-grass, normal walking cannot trigger its table, so the PR #95 debug-prepared Bagon trade chain would still not be naturally available. [PR #99](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/99) is validating original cave walking and natural Bagon acquisition with real ROM/mGBA controls. Wait for its evidence before a categorical statement about that map.

For an authentic GBA design, distinguish (a) **no overworld roaming sprites**, from (b) **no wild encounters outside grass**. The former can be compatible with standard cave encounters and traditional rods/Surf, whereas the latter excludes significant ordinary species acquisition. **No game policy or source code should be changed automatically on this observation; review first and amend only in a small isolated branch with affected-case regression tests.**
