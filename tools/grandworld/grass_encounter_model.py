#!/usr/bin/env python3
"""Reference logic for grass-only visible encounters. NOT injected into GBA runtime.

A map adapter supplies the actual game's tall-grass metatile classifications.
This small deterministic model tests the movement boundary contract independently
of sprites, SaveBlocks or emulation.
"""
from collections import deque

CARDINAL = ((0, 1), (1, 0), (0, -1), (-1, 0))


def grass_component(start, grass, walkable, occupied=()):
    """Return reachable grass cells using only cardinal movements."""
    grass, walkable, occupied = set(grass), set(walkable), set(occupied)
    eligible = (grass & walkable) - occupied
    if start not in eligible:
        return frozenset()
    seen = {start}
    queue = deque((start,))
    while queue:
        x, y = queue.popleft()
        for dx, dy in CARDINAL:
            nxt = (x + dx, y + dy)
            if nxt in eligible and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return frozenset(seen)


def legal_steps(position, origin_component, grass, walkable, occupied=()):
    """Never allow a wild object to leave its original grass component."""
    eligible = set(origin_component) & set(grass) & set(walkable) - set(occupied)
    x, y = position
    if position not in eligible:
        return ()
    return tuple((x + dx, y + dy) for dx, dy in CARDINAL
                 if (x + dx, y + dy) in eligible)


def next_position(position, component, grass, walkable, occupied, direction):
    """Move by a direction index (0..3), or remain in place on a bad edge."""
    if type(direction) is not int or not 0 <= direction < 4:
        raise ValueError("direction must be one of four cardinal steps")
    dx, dy = CARDINAL[direction]
    target = (position[0] + dx, position[1] + dy)
    return target if target in legal_steps(position, component, grass, walkable, occupied) else position
