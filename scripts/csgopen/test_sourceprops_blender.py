#!/usr/bin/env python3
"""Run with Blender --background --python scripts/csgopen/test_sourceprops_blender.py."""

import sys
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sourceprops_blender as props


class ContinuousCollisionTests(unittest.TestCase):
    def test_selection_preserves_architecture(self):
        for name in ("fallentree_dry01", "construction_stack_plywood_01", "logpile_01"):
            self.assertTrue(props._continuous_collision(f"models/props/{name}.mdl"))
        for name in ("wood_fence", "woodrailing_64", "stairs_trail", "urban_tree_giant01", "shelves_wood"):
            self.assertFalse(props._continuous_collision(f"models/props/{name}.mdl"))

    def test_separated_timber_becomes_closed_continuous_surface(self):
        # Two separated pieces leave a central slot. The hull must close it,
        # retain the outer bounds, and have exactly two faces on every edge.
        points = [(x, y, z) for x in (-3.0, -1.0, 1.0, 3.0) for y in (-2.0, 2.0) for z in (0.0, 1.0)]
        geometry = props.ModelGeometry([
            props.LocalTriangle("wood", tuple(points[index:index + 3]), ((0.0, 0.0),) * 3)
            for index in range(0, 15, 3)
        ] + [props.LocalTriangle("wood", (points[-1], points[0], points[1]), ((0.0, 0.0),) * 3)])
        hull = props._convex_collision(geometry)
        edges = Counter()
        volume = 0.0
        for triangle in hull.triangles:
            a, b, c = (props.Vector(point) for point in triangle.points)
            volume += a.dot(b.cross(c)) / 6
            for index in range(3):
                edges[tuple(sorted((triangle.points[index], triangle.points[(index + 1) % 3])))] += 1
        self.assertTrue(edges)
        self.assertTrue(all(count == 2 for count in edges.values()))
        self.assertAlmostEqual(abs(volume), 24.0)
        vertices = {point for triangle in hull.triangles for point in triangle.points}
        self.assertEqual(tuple(min(p[i] for p in vertices) for i in range(3)), (-3.0, -2.0, 0.0))
        self.assertEqual(tuple(max(p[i] for p in vertices) for i in range(3)), (3.0, 2.0, 1.0))
        # Collision uses the same Source rotation/instance scale as rendering.
        prop = SimpleNamespace(scale=2.0, origin=(10.0, 20.0, 30.0))
        triangle = props.LocalTriangle("collision", ((1.0, 0.0, 0.0),) * 3, ((0.0, 0.0),) * 3)
        point = props._transform(triangle, prop, props._source_matrix((0.0, 90.0, 0.0)))[0]
        for actual, expected in zip(point, (10.0, 22.0, 30.0)):
            self.assertAlmostEqual(actual, expected, places=5)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
