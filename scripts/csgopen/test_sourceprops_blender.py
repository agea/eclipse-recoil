#!/usr/bin/env python3
"""Run with Blender --background --python scripts/csgopen/test_sourceprops_blender.py."""

import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sourceprops_blender as props
import sourcebsp


class ContinuousCollisionTests(unittest.TestCase):
    def test_opaque_body_mask_does_not_disable_glass_alpha_test(self):
        with tempfile.TemporaryDirectory() as directory:
            part = props.ObjPart(Path(directory), "tile", sealed=True,
                                 bindings={"body__0": "body", "glass__0": "glass"})
            part.close(sourcebsp, {"body": "body.dds", "glass": "glass.dds"}, 0.25, {"body"})
            config = (Path(directory) / "obj.cfg").read_text()
            self.assertIn('objalphatest "body__0" 0', config)
            self.assertNotIn('objalphatest "glass__0"', config)
            self.assertIn('objskin "glass__0" "../textures/glass.dds"', config)

    def test_window_frame_keeps_aperture_and_budget(self):
        triangle = props.LocalTriangle("solid", ((-10, -32, 1), (10, 32, 87), (10, -32, 1)), ((0, 0),)*3)
        original = props.ModelGeometry([triangle]*100)
        result = props._window_frame_collision("models/props/de_house/windowframe_54x76.mdl", original)
        self.assertEqual(len(result.triangles), 48)
        for t in result.triangles:
            y, z = (sum(p[a] for p in t.points)/3 for a in (1, 2))
            self.assertFalse(-25 < y < 25 and 8 < z < 80)
        self.assertIs(props._window_frame_collision("unknown.mdl", original), original)
        small = props.ModelGeometry([triangle]*47)
        self.assertIs(props._window_frame_collision("models/props/de_house/windowframe_54x76.mdl", small), small)

    def test_modular_stairs_are_continuous_and_budgeted(self):
        def geometry(back, height, count=242):
            points = ((-64, 0, -10.889), (64, back, height), (64, 0, 3))
            return props.ModelGeometry([props.LocalTriangle("solid", points, ((0, 0),)*3)]*count)
        step = "models/props/de_vertigo/step_64x32.mdl"
        top = "models/props/de_vertigo/topstep_16x8.mdl"
        for model, back, height, top_z in ((step, -64, 39, 35), (top, -24.32, 7.987, 3)):
            original = geometry(back, height)
            candidate = props._stair_collision_override(model, original)
            self.assertEqual(len(candidate.triangles), 12)
            points = [p for t in candidate.triangles for p in t.points]
            self.assertEqual(min(p[2] for p in points), -10.889)
            self.assertEqual(max(p[2] for p in points), top_z)
            upper = candidate.triangles[:2]
            for t in upper:
                for x, y, z in t.points:
                    self.assertAlmostEqual(z, 3-y*0.5 if model == step else 3)
            small = geometry(back, height, 8)
            self.assertIs(props._stair_collision_override(model, small), small)
        other = geometry(-64, 39)
        self.assertIs(props._stair_collision_override(step.replace("step_64x32", "other_step"), other), other)
        wrong = geometry(-128, 39)
        self.assertIs(props._stair_collision_override(step, wrong), wrong)

    def test_regular_stairs_require_complete_world_support_per_instance(self):
        triangles = []
        for i in range(4):
            corners = [(x, y, z) for x in (-128, 128) for y in (36-i*12, 48-i*12) for z in (0, 8+i*8)]
            seed = props.ModelGeometry([props.LocalTriangle("solid", tuple(corners[j] for j in ids), ((0, 0),)*3)
                                       for ids in ((0, 1, 2), (3, 4, 5), (6, 7, 0))])
            triangles.extend(props._convex_collision(seed).triangles)
        original = props.ModelGeometry(triangles)
        prop = SimpleNamespace(model="stairs_regular.mdl", angles=(0, 0, 0), origin=(0, 0, 0), scale=1)
        def surface(points):
            return SimpleNamespace(points=points)
        world = [surface(((-128, 48, 8), (128, 48, 8), (128, 12, 32))),
                 surface(((-128, 48, 8), (128, 12, 32), (-128, 12, 32))),
                 surface(((-128, 12, 32), (128, 12, 32), (128, 0, 32))),
                 surface(((-128, 12, 32), (128, 0, 32), (-128, 0, 32)))]
        # Counterclockwise viewed from above, as required for walking support.
        world = [surface(tuple(reversed(t.points))) for t in world]
        self.assertTrue(props._regular_stair_shape(prop.model, original))
        self.assertEqual(props._stair_world_collision(prop, original, original, world).triangles, [])
        self.assertIs(props._stair_world_collision(prop, original, original, world[:1]), original)
        low = [surface(tuple((x, y, z-64) for x, y, z in t.points)) for t in world]
        self.assertIs(props._stair_world_collision(prop, original, original, low), original)
        prop.origin = (1024, 0, 0)
        self.assertIs(props._stair_world_collision(prop, original, original, world), original)
        for name in ("arch_stairs.mdl", "autocombine_stairs.mdl", "doorframe.mdl"):
            self.assertFalse(props._regular_stair_shape(name, original))
        tapered = props.ModelGeometry([props.LocalTriangle(t.material, tuple((p[0]*(1-p[2]/64), p[1], p[2]) for p in t.points), t.uvs) for t in triangles])
        self.assertFalse(props._regular_stair_shape("stairs_tapered.mdl", tapered))

    def test_paired_door_leaves_keep_gap_and_triangle_budget(self):
        model = "models/props/de_dust/hr_dust/dust_doors/dust_door_long_doors_01.mdl"
        triangles = []
        for low, high in (((-40, -3, 0), (-8, 3, 80)), ((8, -3, 0), (40, 3, 80))):
            points = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
            seed = props.ModelGeometry([props.LocalTriangle("solid", tuple(points[i] for i in indices), ((0, 0),)*3)
                                       for indices in ((0, 1, 2), (3, 4, 5), (6, 7, 0))])
            triangles.extend(props._convex_collision(seed).triangles)
        original = props.ModelGeometry(triangles)
        fallback = props.ModelGeometry(triangles*4)
        candidate = props._paired_door_collision(model, original, fallback)
        self.assertLess(len(candidate.triangles), len(fallback.triangles))
        self.assertTrue(all(all(p[0] <= -8 for p in t.points) or all(p[0] >= 8 for p in t.points)
                            for t in candidate.triangles))
        points = [p for t in candidate.triangles for p in t.points]
        self.assertEqual(tuple(min(p[i] for p in points) for i in range(3)), (-40, -3, 0))
        self.assertEqual(tuple(max(p[i] for p in points) for i in range(3)), (40, 3, 80))
        self.assertIs(props._paired_door_collision(model.replace('long_doors', 'large_doorframe'), original, fallback), fallback)
        small = props.ModelGeometry(triangles[:4])
        self.assertIs(props._paired_door_collision(model, original, small), small)
        crossing = props.ModelGeometry([props.LocalTriangle("solid", ((-8, 0, 0), (8, 0, 0), (8, 0, 80)), ((0, 0),)*3)])
        self.assertIs(props._paired_door_collision(model, crossing, fallback), fallback)

    def test_curved_stair_override_is_bounded_and_budgeted(self):
        triangle = props.LocalTriangle("solid", ((0, 0, 0),)*3, ((0, 0),)*3)
        geometry = props.ModelGeometry([triangle]*159)
        model = "models/props/de_dust/hr_dust/dust_trims/dust_kasbah_stairs002.mdl"
        candidate = props._stair_collision_override(model, geometry)
        self.assertEqual(len(candidate.triangles), 87)
        points = [p for t in candidate.triangles for p in t.points]
        self.assertTrue(all(-8.1 <= p[0] <= 256.5 and -0.1 <= p[1] <= 256.5 and -146.1 <= p[2] <= 0.1 for p in points))
        small = props.ModelGeometry([triangle]*24)
        self.assertIs(props._stair_collision_override(model, small), small)
        self.assertIs(props._stair_collision_override("models/props/stairs_other.mdl", geometry), geometry)

    def test_general_smoothing_preserves_passages_and_instance_scale(self):
        def geometry(low, high):
            points = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
            return props.ModelGeometry([props.LocalTriangle("solid", tuple(points[i] for i in indices), ((0, 0),) * 3)
                for indices in ((0, 1, 2), (3, 4, 5), (6, 7, 0))])
        compact = geometry((0, 0, 0), (40, 20, 24))
        self.assertTrue(props._smooth_collision_allowed("models/props/chair.mdl", compact, 0.25))
        self.assertFalse(props._smooth_collision_allowed("models/props/chair.mdl", compact, 1.0))
        panel = geometry((0, 0, 0), (120, 64, 24))
        self.assertTrue(props._smooth_collision_allowed("models/props/panel.mdl", panel, 0.25))
        self.assertFalse(props._smooth_collision_allowed("models/props/panel.mdl", panel, 0.25, (90, 0, 0)))
        for name in ("doorframe", "windowframe", "archway", "stairs", "shelves", "floor_panel", "bridge"):
            self.assertFalse(props._smooth_collision_allowed(f"models/props/{name}.mdl", compact, 0.25))
        passage = geometry((0, 0, 0), (120, 20, 96))
        self.assertFalse(props._smooth_collision_allowed("models/props/unknown_frame.mdl", passage, 0.25))

    def test_general_smoothing_closes_small_cavities_without_more_faces(self):
        triangles = []
        for low, high in (((-3, -2, 0), (-1, 2, 1)), ((1, -2, 0), (3, 2, 1))):
            points = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
            seed = props.ModelGeometry([props.LocalTriangle("solid", tuple(points[i] for i in indices), ((0, 0),) * 3)
                for indices in ((0, 1, 2), (3, 4, 5), (6, 7, 0))])
            triangles.extend(props._pile_collision(seed).triangles)
        before = props.ModelGeometry(triangles)
        after = props._smooth_collision(before)
        self.assertLess(len(after.triangles), len(before.triangles))
        self.assertTrue(any(min(p[0] for p in t.points) < 0 < max(p[0] for p in t.points) for t in after.triangles))

    def test_composite_bench_has_flat_surfaces_and_open_leg_spaces(self):
        triangles = []
        bounds = [((0, -6, 4), (4, 6, 5)), ((3, -6, 6), (4, 6, 8))]
        bounds += [((0, y, 0), (4, y + 0.5, 8)) for y in (-4.5, -0.25, 4)]
        for low, high in bounds:
            points = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
            seed = props.ModelGeometry([
                props.LocalTriangle("bench", tuple(points[i] for i in indices), ((0.0, 0.0),) * 3)
                for indices in ((0, 1, 2), (3, 4, 5), (6, 7, 0))
            ])
            triangles.extend(props._pile_collision(seed).triangles)
        collision = props._component_collision(props.ModelGeometry(triangles), bridge_slats=True)
        self.assertEqual(len(collision.triangles), 60)
        for triangle in collision.triangles:
            a, b, c = (props.Vector(p) for p in triangle.points)
            normal = (b - a).cross(c - a).normalized()
            self.assertEqual(sum(abs(v) > 1e-5 for v in normal), 1)
            if min(p[2] for p in triangle.points) < 4:
                self.assertLessEqual(max(p[1] for p in triangle.points) - min(p[1] for p in triangle.points), 0.5)

    def test_support_has_flat_treads_and_keeps_narrow_upper_profile(self):
        triangles = []
        for low, high in (((0, 0, 0), (4, 1, 4)), ((3, 0, 4), (4, 1, 8))):
            corners = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
            seed = props.ModelGeometry([
                props.LocalTriangle("metal", tuple(corners[i] for i in indices), ((0.0, 0.0),) * 3)
                for indices in ((0, 1, 2), (3, 4, 5), (6, 7, 0))
            ])
            triangles.extend(props._pile_collision(seed).triangles)
        collision = props._split_support_collision(triangles, 4)
        self.assertEqual(len(collision.triangles), 24)
        volume = 0.0
        for triangle in collision.triangles:
            a, b, c = (props.Vector(p) for p in triangle.points)
            volume += a.dot(b.cross(c)) / 6
            normal = (b - a).cross(c - a).normalized()
            self.assertEqual(sum(abs(v) > 1e-5 for v in normal), 1)
            self.assertFalse(any(p[0] < 3 and p[2] > 4 for p in triangle.points))
        self.assertAlmostEqual(abs(volume), 20.0)

    def test_sectioned_bench_preserves_open_space(self):
        self.assertTrue(props._sectioned_collision("models/props/de_inferno/bench_wood.mdl"))
        self.assertFalse(props._sectioned_collision("models/props/de_boathouse/tower_benchseat.mdl"))
        parts = []
        for low, high in ((-3.0, -1.0), (1.0, 3.0)):
            points = [(x, y, z) for x in (low, high) for y in (-2.0, 2.0) for z in (0.0, 1.0)]
            seed = props.ModelGeometry([
                props.LocalTriangle("wood", tuple(points[i] for i in indices), ((0.0, 0.0),) * 3)
                for indices in ((0, 1, 2), (3, 4, 5), (6, 7, 0))
            ])
            parts.extend(props._pile_collision(seed).triangles)
        collision = props._component_collision(props.ModelGeometry(parts))
        self.assertEqual(len(collision.triangles), 24)
        for triangle in collision.triangles:
            xs = [point[0] for point in triangle.points]
            self.assertTrue(max(xs) <= -1.0 or min(xs) >= 1.0)
        edges = Counter()
        for triangle in collision.triangles:
            for i in range(3):
                edges[tuple(sorted((triangle.points[i], triangle.points[(i + 1) % 3])))] += 1
        self.assertTrue(all(count == 2 for count in edges.values()))

    def test_bench_slats_bridge_seat_gaps_without_filling_underneath(self):
        parts = []
        for x in (-3.0, 2.0):
            points = [(a, y, z) for a in (x, x + 1.0) for y in (-6.0, 6.0) for z in (4.0, 5.0)]
            seed = props.ModelGeometry([
                props.LocalTriangle("wood", tuple(points[i] for i in indices), ((0.0, 0.0),) * 3)
                for indices in ((0, 1, 2), (3, 4, 5), (6, 7, 0))
            ])
            parts.extend(props._pile_collision(seed).triangles)
        collision = props._component_collision(props.ModelGeometry(parts), bridge_slats=True)
        self.assertEqual(len(collision.triangles), 12)
        self.assertTrue(any(min(p[0] for p in t.points) < 0 < max(p[0] for p in t.points)
                            for t in collision.triangles))
        self.assertTrue(all(4.0 <= p[2] <= 5.0 for t in collision.triangles for p in t.points))

    def test_selection_preserves_architecture(self):
        for name in ("fallentree_dry01", "construction_stack_plywood_01", "logpile_01", "construction_wood_2x4_break_base_01", "construction_wood_2x4_upper_whole_01"):
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
        envelope = props._pile_collision(geometry)
        self.assertEqual(len(envelope.triangles), 12)
        self.assertEqual({p for t in envelope.triangles for p in t.points},
                         {(x, y, z) for x in (-3.0, 3.0) for y in (-2.0, 2.0) for z in (0.0, 1.0)})
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
