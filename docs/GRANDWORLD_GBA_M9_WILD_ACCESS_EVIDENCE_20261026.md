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
