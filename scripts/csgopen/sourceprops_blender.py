#!/usr/bin/env python3
"""Decode Source 1 static props with Blender + Plumber into Eclipse OBJ tiles.

Run this script through Blender's ``--background --python`` entry point.  The
world BSP converter consumes the emitted manifest and places every generated
tile at the same world offset as the compiled BSP mesh.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector


MAX_TRIANGLES_PER_MODEL = 12_000
PROP_TILE_SIZE = 1024.0

# Map units: below crouched body clearance, or narrower than the player.
SMOOTH_PROP_HEIGHT = 10.0
SMOOTH_PROP_WIDTH = 8.0
PASSAGE_PROP_WORDS = ("arch", "door", "window", "gate", "fence", "railing", "stairs",
                      "ladder", "scaffold", "platform", "roof", "wall", "floor",
                      "bridge", "tunnel", "building", "autocombine", "shelves")


def _smooth_collision_allowed(model: str, geometry: ModelGeometry, scale: float, angles=(0.0, 0.0, 0.0)) -> bool:
    """Only close cavities too small to contain a crouched player passage.

    Architectural frames stay exact even when thin. Evaluate instance scale,
    rather than assuming every instance uses the default Source model size.
    """
    name = Path(model.replace("\\", "/")).stem.lower()
    if any(word in name for word in PASSAGE_PROP_WORDS):
        return False
    points = [p for t in geometry.triangles for p in t.points]
    if not points:
        return False
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]
    matrix = _source_matrix(angles)
    corners = [matrix @ Vector((x, y, z)) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    spans = [(max(p[i] for p in corners) - min(p[i] for p in corners)) * abs(scale) for i in range(3)]
    return spans[2] < SMOOTH_PROP_HEIGHT or max(spans[:2]) < SMOOTH_PROP_WIDTH


def _smooth_collision(geometry: ModelGeometry) -> ModelGeometry:
    """Fill small concavities without adding collision faces or render geometry."""
    try:
        candidate = _convex_collision(geometry)
    except ValueError:
        return geometry
    return candidate if len(candidate.triangles) < len(geometry.triangles) else geometry


def _window_frame_collision(model: str, geometry: ModelGeometry) -> ModelGeometry:
    """Keep reviewed House window openings clear of decimated trim faces."""
    frames = {"models/props/de_house/windowframe_54x76.mdl": (1, 87, 8, 80),
              "models/props/de_house/windowframe_54x44.mdl": (0, 54, 7, 47)}
    limits = frames.get(model.replace("\\", "/").lower())
    if limits is None or len(geometry.triangles) < 48:
        return geometry
    points = [p for t in geometry.triangles for p in t.points]
    low = tuple(min(p[a] for p in points) for a in range(3))
    high = tuple(max(p[a] for p in points) for a in range(3))
    bottom, top, sill, lintel = limits
    if low[0] < -10.1 or high[0] > 10.1 or abs(low[1]+32) > .1 or abs(high[1]-32) > .1 or abs(low[2]-bottom) > .1 or abs(high[2]-top) > .1:
        return geometry
    output = []
    for ymin, ymax, zmin, zmax in [(-32, -25, sill, lintel), (25, 32, sill, lintel),
                                   (-32, 32, bottom, sill), (-32, 32, lintel, top)]:
        vertices = [(x, y, z) for z in (zmin, zmax) for y in (ymin, ymax) for x in (low[0], high[0])]
        quads = ((4, 5, 7, 6), (0, 2, 3, 1), (0, 1, 5, 4),
                 (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5))
        output.extend(LocalTriangle("collision", tuple(vertices[i] for i in indices), ((0, 0),)*3)
                      for q in quads for indices in (q[:3], (q[0], q[2], q[3])))
    return ModelGeometry(output)


def _modular_stair_collision(model: str, geometry: ModelGeometry) -> ModelGeometry:
    """Continuous walking surfaces for the reviewed Vertigo stair modules."""
    name = model.replace("\\", "/").lower()
    modules = {
        "models/props/de_vertigo/step_64x32.mdl": (-64.0, 3.0, 35.0),
        "models/props/de_vertigo/topstep_16x8.mdl": (-24.32, 3.0, 3.0),
    }
    if name not in modules or len(geometry.triangles) < 12:
        return geometry
    back, front_z, back_z = modules[name]
    points = [p for t in geometry.triangles for p in t.points]
    low = tuple(min(p[i] for p in points) for i in range(3))
    high = tuple(max(p[i] for p in points) for i in range(3))
    # Reject unexpected variants or scales baked into the mesh. Small floating
    # point differences in the imported nominal dimensions are harmless.
    if abs(low[0]+64) > 0.1 or abs(high[0]-64) > 0.1 or abs(low[1]-back) > 0.1 or abs(high[1]) > 0.1:
        return geometry
    if low[2] >= front_z or high[2] < max(front_z, back_z):
        return geometry
    vertices = [(-64, 0, low[2]), (64, 0, low[2]), (-64, back, low[2]), (64, back, low[2]),
                (-64, 0, front_z), (64, 0, front_z), (-64, back, back_z), (64, back, back_z)]
    quads = ((4, 6, 7, 5), (0, 4, 5, 1), (0, 1, 3, 2),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))
    return ModelGeometry([LocalTriangle("collision", tuple(vertices[i] for i in indices), ((0.0, 0.0),)*3)
                          for q in quads for indices in (q[:3], (q[0], q[2], q[3]))])


def _stair_collision_override(model: str, geometry: ModelGeometry) -> ModelGeometry:
    """Use reviewed continuous surfaces without increasing collision budgets."""
    candidate = _modular_stair_collision(model, geometry)
    if candidate is not geometry:
        return candidate
    if model.replace("\\", "/").lower() != "models/props/de_dust/hr_dust/dust_trims/dust_kasbah_stairs002.mdl":
        return geometry
    path = Path(__file__).with_name("collision-overrides") / "dust_kasbah_stairs002.json"
    triangles = json.loads(path.read_text())["triangles"]
    candidate = ModelGeometry([LocalTriangle("collision", tuple(tuple(p) for p in t), ((0.0, 0.0),)*3) for t in triangles])
    return candidate if len(candidate.triangles) <= len(geometry.triangles) else geometry


def _regular_stair_shape(model: str, original: ModelGeometry) -> bool:
    """Identify low rectangular stair flights without enclosing passages."""
    name = Path(model.replace("\\", "/")).stem.lower()
    if "stair" not in name or any(word in name for word in ("autocombine", "arch", "door", "window", "railing", "building")):
        return False
    levels = defaultdict(list)
    for triangle in original.triangles:
        a, b, c = (Vector(p) for p in triangle.points)
        normal = (b-a).cross(c-a)
        if normal.length and normal.normalized().z > 0.995:
            levels[round((a.z+b.z+c.z)/3)].extend(triangle.points)
    if len(levels) < 3 or len(levels) > 8:
        return False
    heights = sorted(levels)
    rises = [b-a for a, b in zip(heights, heights[1:])]
    if min(rises) < 4 or max(rises) > 20 or max(rises)-min(rises) > 1:
        return False
    centers = [tuple(sum(p[i] for p in levels[h])/len(levels[h]) for i in range(2)) for h in heights]
    run = max(range(2), key=lambda i: abs(centers[-1][i]-centers[0][i]))
    width = 1-run
    points = [p for t in original.triangles for p in t.points]
    low = tuple(min(p[i] for p in points) for i in range(3))
    high = tuple(max(p[i] for p in points) for i in range(3))
    span = high[width]-low[width]
    # Reject curved, tapered or architectural stairs instead of filling passages.
    if span < 64 or high[2]-low[2] > 64 or any(
        max(p[width] for p in levels[h])-min(p[width] for p in levels[h]) < span*0.9 for h in heights):
        return False
    sign = 1 if centers[0][run] > centers[-1][run] else -1
    front = max(sign*p[run] for p in points)
    upper = max(sign*p[run] for p in levels[heights[-1]])
    if front-upper <= 0 or (heights[-1]-heights[0])/(front-upper) > 1:
        return False
    return True


def _stair_world_collision(prop, original: ModelGeometry, fallback: ModelGeometry, world) -> ModelGeometry:
    """Use authored walking surfaces only when they cover the complete flight."""
    if not _regular_stair_shape(prop.model, original):
        return fallback
    import sourcebsp
    transform = _source_matrix(prop.angles)
    samples = []
    for triangle in original.triangles:
        a, b, c = (Vector(p) for p in triangle.points)
        normal = (b-a).cross(c-a)
        if not normal.length or normal.normalized().z < 0.995:
            continue
        points = _transform(triangle, prop, transform)
        center = tuple(sum(p[i] for p in points)/3 for i in range(3))
        samples.append(center)
        samples.extend(tuple(center[i]*0.4+p[i]*0.6 for i in range(3)) for p in points)
    if not samples:
        return fallback
    low = tuple(min(p[i] for p in samples) for i in range(2))
    high = tuple(max(p[i] for p in samples) for i in range(2))
    nearby = [t.points for t in world if all(max(p[i] for p in t.points) >= low[i]-1 and
              min(p[i] for p in t.points) <= high[i]+1 for i in range(2)) and
              sourcebsp._normalize(sourcebsp._cross(sourcebsp._sub(t.points[1], t.points[0]),
                                   sourcebsp._sub(t.points[2], t.points[0])))[2] >= 0.7]
    for p in samples:
        support = sourcebsp._support_floor((p[0], p[1], p[2]+0.1), nearby)
        if support is None or not -1 <= support-p[2] <= 8:
            return fallback
    return ModelGeometry([])


def _paired_door_collision(model: str, original: ModelGeometry, fallback: ModelGeometry) -> ModelGeometry:
    """Flatten each Long A door leaf separately, preserving the opening."""
    if model.replace("\\", "/").lower() != "models/props/de_dust/hr_dust/dust_doors/dust_door_long_doors_01.mdl":
        return fallback
    leaves = [[], []]
    for triangle in original.triangles:
        low, high = min(p[0] for p in triangle.points), max(p[0] for p in triangle.points)
        if low <= 0 <= high:
            return fallback
        leaves[0 if high < 0 else 1].append(triangle)
    if not all(leaves):
        return fallback
    try:
        candidate = ModelGeometry([t for leaf in leaves for t in _convex_collision(ModelGeometry(leaf)).triangles])
    except ValueError:
        return fallback
    return candidate if len(candidate.triangles) <= len(fallback.triangles) else fallback


def _continuous_collision(model: str) -> bool:
    """Only fill cavities on logs and timber piles, never architectural props."""
    name = Path(model.replace("\\", "/")).stem.lower()
    return name.startswith(("fallentree_", "log_", "logs_", "logpile_", "woodpile_", "lumberpile_", "construction_stack_", "construction_wood_2x4_"))


def _pile_collision(geometry: ModelGeometry) -> ModelGeometry:
    """Use twelve flat faces for bundled boards, preserving local outer bounds.

    Bounding in model space preserves instance rotation. Small board bevels and
    slots should not become footholds that catch a player's capsule.
    """
    points = [point for triangle in geometry.triangles for point in triangle.points]
    low = tuple(min(point[i] for point in points) for i in range(3))
    high = tuple(max(point[i] for point in points) for i in range(3))
    corners = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    return _convex_collision(ModelGeometry([
        LocalTriangle("collision", tuple(corners[i] for i in indices), ((0.0, 0.0),) * 3)
        for indices in ((0, 1, 2), (3, 4, 5), (6, 7, 0))
    ]))


def _sectioned_collision(model: str) -> bool:
    """The curved wooden bench needs smooth supports without filling its frame."""
    return model.replace("\\", "/").lower() == "models/props/de_inferno/bench_wood.mdl"


def _split_support_collision(triangles: list[LocalTriangle], height: float, lower_only: bool = False) -> ModelGeometry:
    """Flat lower support and a separate hull following the inclined back."""
    sections = [[], []]
    for triangle in triangles:
        for side, sign in enumerate((-1, 1)):
            if any(sign * (p[2] - height) > 1e-5 for p in triangle.points):
                sections[side].extend(p for p in triangle.points if sign * (p[2] - height) >= -1e-5)
        for i in range(3):
            a, b = triangle.points[i], triangle.points[(i + 1) % 3]
            if (a[2] - height) * (b[2] - height) < 0:
                ratio = (height - a[2]) / (b[2] - a[2])
                point = tuple(a[j] + ratio * (b[j] - a[j]) for j in range(3))
                sections[0].append(point)
                sections[1].append(point)
    output = []
    for side, section in enumerate(sections):
        if lower_only and side:
            continue
        if len(section) < 4:
            continue
        geometry = ModelGeometry([
            LocalTriangle("collision", tuple(section[i:i + 3]), ((0.0, 0.0),) * 3)
            for i in range(0, len(section) - 2, 3)
        ])
        # Include every extreme point even when the point count is not a multiple of three.
        geometry.triangles.append(LocalTriangle("collision", (section[-1], section[-2], section[0]), ((0.0, 0.0),) * 3))
        output.extend((_pile_collision(geometry) if side == 0 else _convex_collision(geometry)).triangles)
    return ModelGeometry(output)


def _component_collision(geometry: ModelGeometry, bridge_slats: bool = False) -> ModelGeometry:
    """Smooth bench slats with flat, separate lower/back supports."""
    parents = list(range(len(geometry.triangles)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    owners = {}
    for index, triangle in enumerate(geometry.triangles):
        for point in triangle.points:
            # Weld material/UV seams at sub-millimetre Source precision.
            key = tuple(round(value, 3) for value in point)
            if key in owners:
                parents[find(index)] = find(owners[key])
            else:
                owners[key] = index
    groups = defaultdict(list)
    for index, triangle in enumerate(geometry.triangles):
        groups[find(index)].append(triangle)
    sections = []
    slats = []
    seat_slats = []
    back_slats = []
    top = max(point[2] for triangle in geometry.triangles for point in triangle.points)
    for triangles in groups.values():
        points = [point for triangle in triangles for point in triangle.points]
        spans = sorted(max(point[i] for point in points) - min(point[i] for point in points) for i in range(3))
        if bridge_slats and spans[2] > 4 * spans[1]:
            slats.extend(triangles)
            if sum(p[2] for p in points) / len(points) < top * 0.6:
                seat_slats.extend(triangles)
            else:
                back_slats.extend(triangles)
        else:
            sections.append(triangles)
    if bridge_slats and seat_slats and back_slats:
        height = max(p[2] for t in seat_slats for p in t.points)
        output = list(_pile_collision(ModelGeometry(seat_slats)).triangles)
        # Join the back directly to the seat, without a thin slot at the seam.
        back = list(back_slats)
        back.extend(LocalTriangle("collision", tuple((p[0], p[1], height) for p in t.points), t.uvs) for t in back_slats)
        output.extend(_pile_collision(ModelGeometry(back)).triangles)
        for triangles in sections:
            output.extend(_split_support_collision(triangles, height, lower_only=True).triangles)
        return ModelGeometry(output)
    if slats:
        # Smooth the seat/back as one surface; only narrow support frames
        # extend below it, preserving the space between the supports.
        sections.append(slats)
    output = []
    for triangles in sections:
        if bridge_slats and triangles is not slats:
            if seat_slats:
                height = max(p[2] for t in seat_slats for p in t.points)
                output.extend(_split_support_collision(triangles, height).triangles)
            else:
                output.extend(triangles)
            continue
        try:
            hull = _convex_collision(ModelGeometry(triangles))
        except ValueError:
            # Planar details cannot form a closed volume; retain those faces.
            output.extend(triangles)
        else:
            output.extend(hull.triangles if len(hull.triangles) <= len(triangles) else triangles)
    return ModelGeometry(output)


def _convex_collision(geometry: ModelGeometry) -> ModelGeometry:
    """Build a closed local hull independently of render decimation."""
    points = {point for triangle in geometry.triangles for point in triangle.points}
    if len(points) < 4:
        raise ValueError("continuous prop collision needs a solid mesh")
    mesh = bmesh.new()
    try:
        vertices = [mesh.verts.new(point) for point in sorted(points)]
        result = bmesh.ops.convex_hull(mesh, input=vertices, use_existing_faces=False)
        unused = set(result["geom_interior"]) | set(result["geom_unused"])
        bmesh.ops.delete(mesh, geom=list(unused), context="VERTS")
        if not mesh.faces or any(not edge.is_manifold for edge in mesh.edges):
            raise ValueError("continuous prop collision hull is not closed")
        bmesh.ops.triangulate(mesh, faces=list(mesh.faces))
        return ModelGeometry([
            LocalTriangle("collision", tuple(tuple(vertex.co) for vertex in face.verts), ((0.0, 0.0),) * 3)
            for face in mesh.faces
        ])
    finally:
        mesh.free()


def _arguments() -> argparse.Namespace:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bsp", required=True, type=Path)
    parser.add_argument("--vpk", required=True, type=Path)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--plumber", required=True, type=Path)
    parser.add_argument("--triangle-budget", type=int, default=300_000)
    parser.add_argument("--scale", type=float, default=0.25)
    return parser.parse_args(arguments)


@dataclass
class LocalTriangle:
    material: str
    points: tuple[tuple[float, float, float], ...]
    uvs: tuple[tuple[float, float], ...]


@dataclass
class ModelGeometry:
    triangles: list[LocalTriangle]


@dataclass
class ObjPart:
    directory: Path
    relative: str
    pending: list[object] = field(default_factory=list)
    triangles: int = 0
    bindings: dict[str, str] = field(default_factory=dict)
    sealed: bool = False

    @property
    def vertices(self) -> int:
        return self.triangles * 3

    def add(self, triangle) -> None:
        self.pending.append(triangle)
        self.triangles += 1

    def seal(self, sourcebsp) -> None:
        if self.sealed:
            return
        with (self.directory / "props.obj").open("wb") as output:
            _stats, material_meshes = sourcebsp._write_render_obj(output, self.pending, "static props")
        self.bindings = {
            mesh: material
            for material, meshes in material_meshes.items()
            for mesh in meshes
        }
        self.pending.clear()
        self.sealed = True

    def close(self, sourcebsp, texture_names: dict[str, str], scale: float,
              opaque_alpha_materials: set[str] | None = None) -> None:
        self.seal(sourcebsp)
        config = ['objload "props.obj"', "mdlcullface 0", f"mdlscale {scale * 100:.9g}", "mdlcollide 0"]
        for mesh, material in sorted(self.bindings.items()):
            texture = texture_names.get(material)
            if texture:
                config.insert(1, f'objskin "{mesh}" "../textures/{texture}"')
                if opaque_alpha_materials and material in opaque_alpha_materials:
                    config.append(f'objalphatest "{mesh}" 0')
        (self.directory / "obj.cfg").write_text("\n".join(config) + "\n", encoding="utf-8")


class TileWriter:
    def __init__(self, root: Path, model_root: str, sourcebsp):
        self.root = root
        self.model_root = model_root
        self.sourcebsp = sourcebsp
        self.parts: list[ObjPart] = []
        self.active: dict[tuple[int, int], ObjPart] = {}
        self.part_counts: Counter[tuple[int, int]] = Counter()

    def add(self, tile: tuple[int, int], triangle, material: str) -> None:
        part = self.active.get(tile)
        if part is None or part.triangles >= MAX_TRIANGLES_PER_MODEL:
            if part is not None:
                part.seal(self.sourcebsp)
            index = self.part_counts[tile]
            self.part_counts[tile] += 1
            suffix = "_".join(str(value).replace("-", "n") for value in tile)
            name = f"tile_{suffix}_{index}"
            directory = self.root / name
            directory.mkdir(parents=True, exist_ok=True)
            part = ObjPart(directory, f"{self.model_root}/{name}")
            self.parts.append(part)
            self.active[tile] = part
        part.add(triangle)


@dataclass
class CollisionObjPart:
    directory: Path
    relative: str
    pending: list[object] = field(default_factory=list)
    triangles: int = 0
    sealed: bool = False

    def add(self, triangle) -> None:
        self.pending.append(triangle)
        self.triangles += 1

    def seal(self, sourcebsp, scale: float) -> None:
        if self.sealed:
            return
        with (self.directory / "collision.obj").open("wb") as output:
            sourcebsp._write_collision_obj(output, self.pending, "solid static props")
        (self.directory / "obj.cfg").write_text(
            "\n".join(
                (
                    'objload "collision.obj"',
                    'objblend "*" 0',
                    "mdlcullface 0",
                    f"mdlscale {scale * 100:.9g}",
                    "mdltricollide 1",
                )
            )
            + "\n",
            encoding="utf-8",
        )
        self.pending.clear()
        self.sealed = True


class CollisionTileWriter:
    def __init__(self, root: Path, model_root: str, sourcebsp, scale: float):
        self.root = root
        self.model_root = model_root
        self.sourcebsp = sourcebsp
        self.scale = scale
        self.parts: list[CollisionObjPart] = []
        self.active: dict[tuple[int, int], CollisionObjPart] = {}
        self.part_counts: Counter[tuple[int, int]] = Counter()

    def add(self, tile: tuple[int, int], triangle) -> None:
        part = self.active.get(tile)
        if part is None or part.triangles >= MAX_TRIANGLES_PER_MODEL:
            if part is not None:
                part.seal(self.sourcebsp, self.scale)
            index = self.part_counts[tile]
            self.part_counts[tile] += 1
            suffix = "_".join(str(value).replace("-", "n") for value in tile)
            name = f"tile_{suffix}_{index}"
            directory = self.root / name
            directory.mkdir(parents=True, exist_ok=True)
            part = CollisionObjPart(directory, f"{self.model_root}/{name}")
            self.parts.append(part)
            self.active[tile] = part
        part.add(triangle)


def _source_matrix(angles: tuple[float, float, float]) -> Matrix:
    pitch, yaw, roll = (math.radians(value) for value in angles)
    sp, cp = math.sin(pitch), math.cos(pitch)
    sy, cy = math.sin(yaw), math.cos(yaw)
    sr, cr = math.sin(roll), math.cos(roll)
    return Matrix(
        (
            (cp * cy, sr * sp * cy - cr * sy, cr * sp * cy + sr * sy),
            (cp * sy, sr * sp * sy + cr * cy, cr * sp * sy - sr * cy),
            (-sp, sr * cp, cr * cp),
        )
    )


def _mesh_objects(root):
    objects = [root, *root.children_recursive]
    return [obj for obj in objects if obj.type == "MESH"]


def _protected_component_count(mesh) -> int:
    """Count disconnected islands large enough to expose visible wall holes."""
    polygons = mesh.polygons
    if not polygons:
        return 0
    parents = list(range(len(polygons)))

    def find(value: int) -> int:
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    def union(left: int, right: int) -> None:
        left, right = find(left), find(right)
        if left != right:
            parents[right] = left

    owners = {}
    for polygon in polygons:
        for vertex in polygon.vertices:
            owner = owners.setdefault(vertex, polygon.index)
            union(owner, polygon.index)
    areas = defaultdict(float)
    for polygon in polygons:
        areas[find(polygon.index)] += polygon.area
    # Source models use Source units.  Islands smaller than 16x32 units are
    # typically bars, bolts, leaves, or trim rather than architectural panels.
    return sum(area >= 512.0 for area in areas.values())


def _append_object_geometry(output, root, original, ratio: float, minimum_triangles: int) -> None:
    modifier = None
    polygon_count = len(original.data.polygons)
    if ratio < 0.999 and polygon_count > 3:
        modifier = original.modifiers.new("csgopen_simplify", "DECIMATE")
        modifier.ratio = max(ratio, min(1.0, minimum_triangles / polygon_count))
        bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = original.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        uv_data = mesh.uv_layers.active.data if mesh.uv_layers.active else None
        local_matrix = root.matrix_world.inverted() @ original.matrix_world
        materials = [
            (material.get("path_id") or material.name) if material else "missing"
            for material in original.data.materials
        ]
        for polygon in mesh.loop_triangles:
            material = materials[polygon.material_index] if polygon.material_index < len(materials) else "missing"
            points = tuple(tuple(local_matrix @ mesh.vertices[index].co) for index in polygon.vertices)
            uvs = tuple(tuple(uv_data[loop].uv) if uv_data else (0.0, 0.0) for loop in polygon.loops)
            output.append(LocalTriangle(material, points, uvs))
    finally:
        evaluated.to_mesh_clear()
        if modifier is not None:
            original.modifiers.remove(modifier)


def _geometry(root, ratio: float, structural: bool) -> ModelGeometry:
    output = []
    for original in _mesh_objects(root):
        # Preserve a reserve for every sizeable disconnected architectural
        # island.  Tiny bars, bolts, and leaves do not consume the reserve, so
        # the model remains light while wall/door panels cannot all disappear.
        components = _protected_component_count(original.data) if structural else 1
        minimum_triangles = max(24, components * 8)
        _append_object_geometry(output, root, original, ratio, minimum_triangles)
    return ModelGeometry(output)


def _transform(triangle: LocalTriangle, prop, matrix: Matrix):
    points = []
    for point in triangle.points:
        transformed = matrix @ (Vector(point) * prop.scale)
        points.append(tuple(transformed[index] + prop.origin[index] for index in range(3)))
    return tuple(points)


def _extract_pak_models(bsp, models: set[str], destination: Path) -> None:
    stems = {model.lower().removesuffix(".mdl") for model in models}
    if not bsp.pakfile:
        return
    with zipfile.ZipFile(io.BytesIO(bsp.pakfile)) as archive:
        for name in archive.namelist():
            normalized = name.replace("\\", "/").lower()
            if normalized.startswith("/") or ".." in Path(normalized).parts:
                continue
            # Plumber resolves MDL material paths through VMT existence even
            # when material import is disabled. Keep BSP-local definitions
            # available so custom props retain their texture bindings.
            material = normalized.startswith("materials/") and normalized.endswith(".vmt")
            if material or any(normalized == stem + extension for stem in stems for extension in (".mdl", ".vvd", ".dx90.vtx", ".phy")):
                target = destination / normalized
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))


def main() -> int:
    args = _arguments()
    scripts = Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts))
    sys.path.insert(0, str(args.plumber.resolve().parent))
    import sourcebsp
    from plumber.asset import AssetCallbacks
    from plumber.plumber import FileSystem, Importer

    bsp = sourcebsp.SourceBsp.read(args.bsp.read_bytes(), args.bsp.name)
    bounds = bsp.playable_bounds()
    props = [
        prop
        for prop in bsp.static_props
        if not bounds
        or all(bounds[0][axis] - 512 <= prop.origin[axis] <= bounds[1][axis] + 512 for axis in range(3))
    ]
    usage = Counter(prop.model.lower() for prop in props)
    models = set(usage)
    structural_keywords = (
        "autocombine",
        "arch",
        "column",
        "curb",
        "door",
        "fence",
        "floor",
        "gate",
        "kasbah",
        "platform",
        "railing",
        "roof",
        "scaffold",
        "stairs",
        "trim",
        "wall",
        "window",
    )
    structural_models = {
        prop.model.lower()
        for prop in props
        if prop.solid or any(keyword in prop.model.lower() for keyword in structural_keywords)
    }
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    with tempfile.TemporaryDirectory(prefix="csgopen-source-pak-") as temporary:
        extracted = Path(temporary)
        _extract_pak_models(bsp, models, extracted)
        filesystem = FileSystem("CS:GO", [("DIR", str(extracted)), ("VPK", str(args.vpk))])
        callbacks = AssetCallbacks(bpy.context)
        imported = {}
        failures = {}
        weighted_triangles = 0
        structural_weighted_triangles = 0
        for number, model in enumerate(sorted(models), 1):
            try:
                importer = Importer(filesystem, callbacks, 4, import_materials=False)
                importer.import_mdl(model, True, import_animations=False)
                root = callbacks.model_tracker.get_last_imported()
                if root is None:
                    raise RuntimeError("decoder returned no model")
                triangles = sum(len(obj.data.polygons) for obj in _mesh_objects(root))
                imported[model] = (root, triangles)
                weighted_triangles += triangles * usage[model]
                if model in structural_models:
                    structural_weighted_triangles += triangles * usage[model]
            except (OSError, RuntimeError) as error:
                failures[model] = str(error)
            if number % 100 == 0:
                print(f"[csgopen] decoded {number}/{len(models)} prop models", flush=True)

        ratio = min(1.0, args.triangle_budget / max(weighted_triangles, 1))
        stem = args.bsp.stem
        model_root = f"csgopen/imported/{stem}/props"
        output_root = args.stage / "data" / model_root
        output_root.mkdir(parents=True, exist_ok=True)
        writer = TileWriter(output_root, model_root, sourcebsp)
        collision_root = f"csgopen/imported/{stem}/prop_collision"
        collision_writer = CollisionTileWriter(
            args.stage / "data" / collision_root,
            collision_root,
            sourcebsp,
            args.scale,
        )
        geometry_cache = {}
        stair_original_cache = {}
        stair_world = None
        collision_cache = {}
        sectioned_cache = {}
        continuous_props = 0
        sectioned_props = 0
        smooth_props = 0
        smooth_cache = {}
        written_props = 0
        solid_props = 0
        for number, prop in enumerate(props, 1):
            item = imported.get(prop.model.lower())
            if item is None:
                continue
            if prop.model.lower() not in geometry_cache:
                original_triangles = item[1]
                minimum_ratio = min(1.0, 24 / max(original_triangles, 1))
                geometry_cache[prop.model.lower()] = _geometry(
                    item[0],
                    max(ratio, minimum_ratio),
                    prop.model.lower() in structural_models,
                )
            geometry = geometry_cache[prop.model.lower()]
            collision = _window_frame_collision(prop.model, _stair_collision_override(prop.model, geometry)) if prop.solid else geometry
            if prop.solid and "stair" in Path(prop.model).stem.lower() and collision is geometry:
                if prop.model.lower() not in stair_original_cache:
                    stair_original_cache[prop.model.lower()] = _geometry(item[0], 1.0, True)
                original = stair_original_cache[prop.model.lower()]
                if _regular_stair_shape(prop.model, original):
                    if stair_world is None:
                        stair_world = bsp.playable_collision_triangles(2)
                    collision = _stair_world_collision(prop, original, geometry, stair_world)
            if prop.solid and prop.model.lower() == "models/props/de_dust/hr_dust/dust_doors/dust_door_long_doors_01.mdl":
                if prop.model.lower() not in collision_cache:
                    original = _geometry(item[0], 1.0, True)
                    collision_cache[prop.model.lower()] = _paired_door_collision(prop.model, original, geometry)
                collision = collision_cache[prop.model.lower()]
            elif prop.solid and _continuous_collision(prop.model):
                if prop.model.lower() not in collision_cache:
                    original = _geometry(item[0], 1.0, True)
                    name = Path(prop.model).stem.lower()
                    collision_cache[prop.model.lower()] = (
                        _pile_collision(original) if name.startswith(("construction_stack_", "construction_wood_2x4_"))
                        else _convex_collision(original)
                    )
                collision = collision_cache[prop.model.lower()]
                continuous_props += 1
            elif prop.solid and _sectioned_collision(prop.model):
                if prop.model.lower() not in sectioned_cache:
                    candidate = _component_collision(geometry, bridge_slats=True)
                    # Respect even unusually small user-supplied prop budgets.
                    sectioned_cache[prop.model.lower()] = candidate if len(candidate.triangles) <= len(geometry.triangles) else geometry
                collision = sectioned_cache[prop.model.lower()]
                sectioned_props += 1
            elif prop.solid and collision is geometry and _smooth_collision_allowed(prop.model, geometry, args.scale * prop.scale, prop.angles):
                if prop.model.lower() not in smooth_cache:
                    smooth_cache[prop.model.lower()] = _smooth_collision(geometry)
                collision = smooth_cache[prop.model.lower()]
                if collision is not geometry:
                    smooth_props += 1
            transform = _source_matrix(prop.angles)
            tile = (math.floor(prop.origin[0] / PROP_TILE_SIZE), math.floor(prop.origin[1] / PROP_TILE_SIZE))
            for triangle in geometry.triangles:
                points = _transform(triangle, prop, transform)
                transformed = sourcebsp.Triangle(triangle.material, points, triangle.uvs)
                writer.add(tile, transformed, triangle.material)
            if prop.solid:
                for triangle in collision.triangles:
                    points = _transform(triangle, prop, transform)
                    collision_writer.add(tile, sourcebsp.Triangle(triangle.material, points, triangle.uvs))
                solid_props += 1
            written_props += 1
            if number % 250 == 0:
                print(f"[csgopen] instanced {number}/{len(props)} static props", flush=True)

        for part in writer.parts:
            part.seal(sourcebsp)
        for part in collision_writer.parts:
            part.seal(sourcebsp, args.scale)
        materials = {material for part in writer.parts for material in part.bindings.values()}
        texture_dir = output_root / "textures"
        texture_dir.mkdir(parents=True, exist_ok=True)
        content = sourcebsp.ContentStore(bsp.pakfile, sourcebsp.VpkArchive(args.vpk))
        dummy_meshes = {material: [material] for material in materials}
        texture_names = {}
        texture_stats = sourcebsp._extract_materials(content, dummy_meshes, texture_dir, texture_names)
        opaque_alpha_materials = {
            material for material in materials if sourcebsp._has_opaque_alpha_mask(content, material)
        }
        for part in writer.parts:
            part.close(sourcebsp, texture_names, args.scale, opaque_alpha_materials)

    manifest = {
        "models": [part.relative for part in writer.parts]
        + [part.relative for part in collision_writer.parts],
        "counts": {
            "source_props": len(bsp.static_props),
            "playable_props": len(props),
            "written_props": written_props,
            "source_models": len(models),
            "decoded_models": len(imported),
            "failed_models": len(failures),
            "source_weighted_triangles": weighted_triangles,
            "source_structural_triangles": structural_weighted_triangles,
            "structural_models": len(structural_models),
            "triangles": sum(part.triangles for part in writer.parts),
            "vertices": sum(part.vertices for part in writer.parts),
            "tile_models": len(writer.parts),
            "solid_props": solid_props,
            "continuous_collision_props": continuous_props,
            "continuous_collision_models": sorted(collision_cache),
            "sectioned_collision_props": sectioned_props,
            "sectioned_collision_models": sorted(sectioned_cache),
            "smooth_collision_props": smooth_props,
            "smooth_collision_policy": "compact-world-bounds-v1",
            "smooth_collision_models": sorted(smooth_cache),
            "collision_triangles": sum(part.triangles * 2 for part in collision_writer.parts),
            "collision_tile_models": len(collision_writer.parts),
            "simplification_ratio": ratio,
        },
        "textures": texture_stats,
        "failures": failures,
    }
    manifest_path = args.stage / f"{args.bsp.stem}-props.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
