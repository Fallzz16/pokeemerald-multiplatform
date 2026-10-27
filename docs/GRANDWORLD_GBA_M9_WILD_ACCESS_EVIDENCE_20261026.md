# Grand World GBA M9 — Wildlife / Pokédex Acceptance Snapshot (26 Oct 2026)

> ONLY the real ARM GBA cartridge; NOT the unrelated Grand World Online web game.
> Work in draft branches only; original pinned PKMN-World engine, M8 stable branch,
> PT-BR work, save-block structure and species IDs are preserved.
> NEVER attach/distribute any ROM or real save in a CI artifact.

## Already proven — do NOT repeat without cause

- Existing M8 world/save matrix: 51 World suites, plus 702 PT-BR ROM-bound checks
  for six hero profiles, Save/Continue and cross-region continuity:
  https://github.com/Fallzz16/pokeemerald-multiplatform/pull/80
- Six protagonists selected using actual intro menus: 96/96 ROM-bound mGBA:
  https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40296022578
- Wild battle from physical walking through tall grass, Route37: 12/12 mGBA:
  https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40303963974
- Separate actual battle-cycle cases: 15/15 RUN/flee, 18/18 Master Ball
  capture/add-to-party/return to overworld on disposable sessions:
  https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40306858033

## New source / experimental evidence in this iteration

1. **Original-source audit:** 484 mapped encounter records, 36 species
   in disabled water/fishing/rock tables but absent from all land tables.
   The number does NOT establish 36 globally unobtainable Pokémon.
   PR #84: https://github.com/Fallzz16/pokeemerald-multiplatform/pull/84
2. **Experimental same-route proposal:** 17 routes initially had possible
   land slots, but actual mGBA metatile survey found Route111 has zero
   tall-grass tiles. Route130 is an ocean map and also excluded.
   Evidence-gated rerun: **16 proposed experimental land entries**,
   **20 without a suitable already-surveyed candidate route**, 12/12 new
   source guard tests, modern ARM cartridge built in disposable checkout.
   No version/stable wild table was patched or merged.
   https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40313368346
3. **New actual ROM gameplay for ONE proposal:** Qwilfish (species 211)
   appeared spontaneously in Route32 grass on the experimental cartridge,
   after 40 physical steps and two real wild encounters; 8/8 mGBA checks.
   This does NOT certify the other 15 proposals or their habitat quality.
   https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40316499670
4. **Evolution graph source audit, 7/7 tests:** original 36 risk species,
   mutually exclusive source classifications:
     - 13 new experimental direct land slots (others already have
       a source evolution route);
     - 4 source evolution paths from pre-existing land-table species:
       Dragonair (Dratini), Forretress (Pineco), Magcargo (Slugma),
       Pelipper (Wingull);
     - 6 evolution paths depending on experimental species:
       Gyarados (Magikarp), Lanturn (Chinchou), Seaking (Goldeen),
       Sharpedo (Carvanha), Wailord (Wailmer), Whiscash (Barboach);
     - 13 with no identified land/evolution path.
   This scan is NOT evidence evolution prerequisites actually work.
   https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40316082335
5. **Scripted event scan, 7/7 tests:** 1,141 pinned World map scripts.
   Lapras has a gift opcode in SilphCo_7F_Frlg and scripted encounter in
   UnionCave_B2F. The other 12 residual species had no direct
   givemon/giveegg/setwildbattle in this LIMITED scan.
   https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40316833046
6. **Source trade scan, 7/7 tests:** in-game trade offers Horsea for Bagon,
   with Bagon in original land tables; Horsea -> Seadra level32 exists
   in the source evolution graph. Actual NPC access, catch, trade,
   evolution and story prerequisites are NOT yet gameplay-certified.
   https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40317386041

## Still without a source land/evolution, direct map scripted event,
## or in-game trade offer lead in the LIMITED scans

Clamperl, Finneon, Luvdisc, Mantine, Nosepass, Octillery, Relicanth,
Remoraid, Shellder, Shellos.

Do NOT label these globally unobtainable yet: indirect gifts, trades with
dynamic species inputs, eggs, other nonstandard events, breeding, and
other acquisition mechanisms have NOT been exhausted.

## Prioritized next genuinely missing tests (not repeats)

1. Live capture/reception of original SilphCo Lapras, or Union Cave
   Lapras (event reachability, flag and party/PC storage).
2. Actual player trade of Bagon for Horsea and subsequent Horsea ->
   Seadra; verify prerequisites before labelling normal-gameplay accessible.
3. Representative / remaining 15 experimental species-route pairs:
   ensure actual walkable grass, random wild encounter, catchability,
   sensible habitat and level, and consistency across day/night.
4. For the ten residual species, inventory previously untested indirect
   acquisition paths; propose location-appropriate encounters only after
   those source and gameplay checks.
5. Once accepted, run ONLY the regression cases materially affected by
   actual production wild-table changes; never automatically merge to M8.

All new PRs remain draft. Release readiness remains FALSE.


## Consolidated 36-species matrix (27 Oct 2026)

This is a **source-evidence summary**, NOT a ROM-release checklist and NOT a declaration that these Pokemon are globally unobtainable. Exact input artifacts: [initial 36-source inventory](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40300985431), [16 grass-gated provisional routes](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40313368346), [36-species lineage classification](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40316082335), [script search](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40316833046), and [trade search](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40317386041). These reports use original encounter-table SHA256 `c6eb187450227f0bccc40241f7f7820f4a8cbf7574dcaab17141bdba86bb01d3`.

**Classification is mutually exclusive for the 36 originally at-risk species:** 4 original-land evolution paths, 13 experimental-only direct land, 6 evolution paths dependent on experiments, 13 residual with no recognized grass/evolution path. There are **zero original direct land-table entries** among the 36 *by definition*; the original source also lists 257 other land species. The 16 proposed grass placements comprise the **13 experimental-only direct** rows **plus 3 original-evolution** rows (Dragonair, Forretress, Pelipper); these two classifications must NOT be added to imply 39 species. The Route111 proposal was rejected after zero actual grass tiles were observed.

### Original land evolution (4)

EVO_LEVEL path starts from a species in an original terrestrial table. Candidate map is an optional, unapproved direct encounter (where listed).

| Species | Source / dependency | Method / route | Gameplay evidence |
|---|---|---|---|
| Dragonair | Original land parent: Dratini | Route 45 | Source graph only; unapproved direct grass proposal if mapped |
| Forretress | Original land parent: Pineco | Route 28 | Source graph only; unapproved direct grass proposal if mapped |
| Magcargo | Original land parent: Slugma | — | Source graph only; unapproved direct grass proposal if mapped |
| Pelipper | Original land parent: Wingull | Route 104 | Source graph only; unapproved direct grass proposal if mapped |

### New experimental land only (13)

No original terrestrial path established; all listed grass placements remain unmerged experiments. Only Qwilfish's *natural appearance* in Route 32 is proven in mGBA; biome acceptance and actual capture of new entries are not.

| Species | Source / dependency | Method / route | Gameplay evidence |
|---|---|---|---|
| Barboach | Candidate `Route 114` | Experimental-only | No individual natural-spawn proof |
| Buizel | Candidate `Route 30` | Experimental-only | No individual natural-spawn proof |
| Carvanha | Candidate `Route 118` | Experimental-only | No individual natural-spawn proof |
| Chinchou | Candidate `Route 47` | Experimental-only | No individual natural-spawn proof |
| Corphish | Candidate `Route 102` | Experimental-only | No individual natural-spawn proof |
| Goldeen | Candidate `Route 42` | Experimental-only | No individual natural-spawn proof |
| Magikarp | Candidate `Route 103` | Experimental-only | No individual natural-spawn proof |
| Poliwag | Candidate `Route 35` | Experimental-only | No individual natural-spawn proof |
| Poliwhirl | Candidate `Route 44` | Experimental-only | No individual natural-spawn proof |
| Qwilfish | Candidate `Route 32` | Experimental-only | 8/8 natural mGBA spawn, NOT habitat approval |
| Staryu | Candidate `Route 34` | Experimental-only | No individual natural-spawn proof |
| Tentacool | Candidate `Route 115` | Experimental-only | No individual natural-spawn proof |
| Wailmer | Candidate `Route 121` | Experimental-only | No individual natural-spawn proof |

### Evolution dependent on experimental land (6)

Source EVO_LEVEL path exists, but the parent is itself experimentally placed; neither parent availability in stable M8 nor the specific evolution in gameplay is certified.

| Species | Source / dependency | Method / route | Gameplay evidence |
|---|---|---|---|
| Gyarados | Magikarp (experimental) | EVO_LEVEL | Evolution itself not tested |
| Lanturn | Chinchou (experimental) | EVO_LEVEL | Evolution itself not tested |
| Seaking | Goldeen (experimental) | EVO_LEVEL | Evolution itself not tested |
| Sharpedo | Carvanha (experimental) | EVO_LEVEL | Evolution itself not tested |
| Wailord | Wailmer (experimental) | EVO_LEVEL | Evolution itself not tested |
| Whiscash | Barboach (experimental) | EVO_LEVEL | Evolution itself not tested |

### No recognized grass/evolution path (13)

These are residual rows of the source-level evolution audit; 10 have no lead under the *limited* script/trade scans. This does NOT prove global impossibility; special/indirect sources and campaign reachability are unverified.

| Species | Source / dependency | Method / route | Gameplay evidence |
|---|---|---|---|
| Clamperl | No additional direct source lead | Residual source audit | No certification of normal playthrough |
| Finneon | No additional direct source lead | Residual source audit | No certification of normal playthrough |
| Horsea | Trade: original NPC offers Horsea for Bagon (not gameplay-certified completion) | Residual source audit | No certification of normal playthrough |
| Lapras | Silph Co. 7F gift; Union Cave B2F scripted battle (not gameplay-certified access) | Residual source audit | No certification of normal playthrough |
| Luvdisc | No additional direct source lead | Residual source audit | No certification of normal playthrough |
| Mantine | No additional direct source lead | Residual source audit | No certification of normal playthrough |
| Nosepass | No additional direct source lead | Residual source audit | No certification of normal playthrough |
| Octillery | No additional direct source lead | Residual source audit | No certification of normal playthrough |
| Relicanth | No additional direct source lead | Residual source audit | No certification of normal playthrough |
| Remoraid | No additional direct source lead | Residual source audit | No certification of normal playthrough |
| Seadra | Possible level-32 evolution from traded Horsea (dependent) | Residual source audit | No certification of normal playthrough |
| Shellder | No additional direct source lead | Residual source audit | No certification of normal playthrough |
| Shellos | No additional direct source lead | Residual source audit | No certification of normal playthrough |

### Verified/new live gates and unresolved trade

- [PR #94](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/94) passed 11/11 real mGBA checks of walking to PacifidlogTown House3 trade NPC and declining safely ([run 40322180238](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40322180238)); NOT a completed trade.
- [PR #95](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/95) used a source-verified level-15 Bagon prepared **by debug menu only**, got 9/12 real mGBA checks on [run 40464068631](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40464068631). Screenshots exposed an unselected storage/BOX1 grid; the original test never navigated to party Bagon. It does **not** establish a broken trade engine or successful receiving of Horsea. A narrower cursor-navigation correction is now committed on the PR #95 branch; check its *new* CI before upgrading status.
- **Seadra remains conditional** on Horsea access and its real level-32 evolution. **Lapras remains conditional** on reaching and completing gift/event scripts. None of the ten residual species without these named leads is certified unobtainable by indirect methods.
- No source encounters, species IDs, compiled game, PT-BR baseline, saves, story scripts, or original M8 stable branch were edited by this report. Avoid grass placement of aquatic species (particularly Magikarp, Tentacool, Qwilfish) without an explicit habitat-design decision.

### Release / future-test gates

First close the in-game trade UI loop in the existing PR #95. Next target a previously untested Lapras gift/Union Cave event, then source-dependent evolution, and only then biome-appropriate wild redistributions. Existing pass evidence for Route32 Qwilfish, hero selection, wild capture/flee, saves and intro is intentionally **not rerun**. Full 36-species Pokédex availability is **NOT** approved.


### Live update: Bagon-for-Horsea completed (27 Oct 2026)

- [PR #95](https://github.com/Fallzz16/pokeemerald-multiplatform/pull/95), [real ARM GBA/mGBA run #40465755959](https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40465755959): **12/12 exact-ROM-bound PASS** on commit `117956b9e6fa95c4e126a876f4a22ffa649effc5`.
- Original PacifidlogTown House3 trader: real player movement and controller-driven storage `Left, Up, A, A` selects a valid Bagon; trade animation completes, source flag 0x9A becomes set, encrypted party species changes from Bagon 371 to Horsea 116, party count remains one, return to original map is verified, no fatal screen.
- **Caveat**: Bagon provided through original debug Give Pokemon UI, NPC location reached through original debug warp. This proves **actual trade mechanics**, not natural Bagon capture, reachability via story progression or normal no-debug completion. Horsea -> Seadra level-32 remains untested; no game data modified.
- Prior 9/12 run #40464068631 was a test navigation failure (left stranded at BOX1 selection), fixed by test-only cursor movement, not a new game mechanic.
