# M8 experimental visible grass encounters — approved behavior

The player has clarified that **visible wild Pokémon replace random encounters in tall grass only**. They are **not** free-roaming Pokémon in caves, water, roads, cities or any other terrain. Following Pokémon are an independent feature.

## Hard rules
1. Spawn only on a walkable tile whose **metatile behavior is tall grass**, subject to the current map's original encounter table. Use the engine's actual metatile classification, not a visual color/tileset approximation.
2. A wild Pokémon can move only to an adjacent, walkable grass tile within the **same connected grass patch** in which it spawned. Reject borders, ledges, impassable tiles, objects, occupied tiles, map transitions and other terrain.
3. Start a normal wild battle only on physical contact with a visible Pokémon; preserve level/species/held item/shiny personality selected at spawn. Never roll a second independent encounter on collision.
4. While the feature is active and a visible population is supported on the map, suppress **step-triggered encounters in grass only**. Fishing, surfing, scripted, rock smash and other encounter channels remain unchanged. If a map cannot safely spawn a visible population, use an explicit fallback policy and test it.
5. No wandering onto pathways, buildings, water, short grass, cave floors or connected routes. Deactivate objects on leaving the map.
6. Derive rarity from the existing encounter tables. Time-of-day filtering may be added only after the base model is reliable. Shiny appearance must reflect the same personality as the battle.
7. Spawn count must respect actual free object-event slots, VRAM/OAM and performance budgets and scale dynamically. No hard-coded promise of eight or any other count.
8. Never add fields to SaveBlock1/2/3 in the initial experiment. Visible objects are transient and reconstructed on reentry; preserve region travel, party, and save/reload semantics.
9. Followers are independent player-controlled team Pokémon and must not consume wild encounter RNG or trigger battle on contact.
10. A single release flag must allow experiment off without changing existing M8 gameplay. No certification count increases from code inspection.

## State machine
- On grass map load: collect spawn candidates from permitted grass tiles and connected components.
- Spawn: choose species/level using the **existing map-specific weighted tables**; instantiate object only if its spawn location is free and valid.
- Tick: occasionally choose a cardinal step; move only if destination is in the spawn component and grass-classified.
- Contact: freeze object and snapshot its preselected battle identity; call standard wild battle path; remove/update visible object afterward.
- Despawn: reclaim transient objects on map transition, battle, follower conflict or resource pressure.
- Disable: original step encounters remain active until the feature and its tests are explicitly enabled.

## Required emulator acceptance
- Pokémon never step off grass even at narrow boundaries, islands and grass beside water or exits.
- No classic step encounters while visible mode active in supported grass; classic encounters unaffected in non-grass channels.
- Collision produces exactly the shown Pokémon, including level and shiny state.
- OAM/object-event saturation degrades gracefully; no blocked trainers or NPC scripts.
- Save/reload, six region crossings, followers, 43 experimental families, title and battle regressions still pass.

**This file specifies an experiment. It does not claim the runtime implementation is complete.**
