"""Boundary regressions for the standalone grass-only encounter movement model."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "grass_encounter_model.py"
spec = importlib.util.spec_from_file_location("grass_model", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class GrassMovementTests(unittest.TestCase):
    def test_never_leaves_grass_boundary(self):
        grass = {(1, 1), (1, 2), (2, 2)}
        world = {(x, y) for x in range(4) for y in range(4)}
        part = g.grass_component((1, 1), grass, world)
        self.assertEqual(part, grass)
        pos = (1, 1)
        for _ in range(100):
            for direction in range(4):
                pos = g.next_position(pos, part, grass, world, (), direction)
                self.assertIn(pos, grass)

    def test_isolated_patch_not_crossed_even_if_nearby(self):
        grass = {(1, 1), (1, 2), (3, 2)}
        walkable = {(x, y) for x in range(5) for y in range(5)}
        component = g.grass_component((1, 1), grass, walkable)
        self.assertNotIn((3, 2), component)

    def test_blocked_tiles_and_occupied_tiles(self):
        grass = {(1, 1), (1, 2), (2, 2)}
        self.assertEqual(g.grass_component((1, 1), grass, grass - {(1, 2)}),
                         frozenset({(1, 1)}))
        component = g.grass_component((1, 1), grass, grass)
        self.assertEqual(g.legal_steps((1, 1), component, grass, grass, {(1, 2)}), ())

    def test_invalid_spawn_and_direction(self):
        self.assertFalse(g.grass_component((0, 0), {(1, 1)}, {(1, 1)}))
        with self.assertRaises(ValueError):
            g.next_position((1, 1), {(1, 1)}, {(1, 1)}, {(1, 1)}, (), 7)

    def test_dynamic_grass_removal_cannot_be_crossed(self):
        grass = {(1, 1), (1, 2)}
        component = g.grass_component((1, 1), grass, grass)
        self.assertEqual(g.legal_steps((1, 1), component, {(1, 1)}, grass), ())


if __name__ == "__main__":
    unittest.main()
