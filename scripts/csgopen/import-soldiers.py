#!/usr/bin/env python3
"""Adapt locally installed Urban Terror 4.3 soldiers to Eclipse Recoil MD3s.

Source configurations are parsed as data, never executed. Derived assets remain
in an ignored local ZIP; the release packager deliberately excludes that ZIP.
"""

import argparse
import fnmatch
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import zipfile

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
PREFIX = "actors/soldier"
HEADER = struct.Struct("<4si64s9i")
TAG = struct.Struct("<64s12f")
MESH = struct.Struct("<4s64s10i")
IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)


class ImportError(ValueError):
    pass


class Assets:
    def __init__(self, folder):
        folder = folder / "q3ut4" if (folder / "q3ut4").is_dir() else folder
        self.archives = [zipfile.ZipFile(p) for p in sorted(folder.glob("*.pk3"))]
        self.files = {name: z for z in self.archives for name in z.namelist()}
        self.used = {}

    def read(self, name):
        if name not in self.files:
            raise ImportError(f"Missing Urban Terror asset: {name}")
        data = self.files[name].read(name)
        self.used[name] = {"archive": Path(self.files[name].filename).name,
                           "sha256": hashlib.sha256(data).hexdigest()}
        return data

    def close(self):
        for z in self.archives:
            z.close()


def header(data):
    if len(data) < HEADER.size:
        raise ImportError("Truncated MD3 header")
    h = list(HEADER.unpack_from(data))
    if h[:2] != [b"IDP3", 15] or h[4] < 1 or h[5] < 0 or h[6] < 1:
        raise ImportError("Unsupported MD3 header")
    if not (HEADER.size <= h[8] <= h[9] <= h[10] <= h[11] == len(data)):
        raise ImportError("Invalid MD3 offsets")
    if h[8] + h[4] * 56 > h[9] or h[9] + h[4] * h[5] * TAG.size > h[10]:
        raise ImportError("Truncated MD3 frames/tags")
    return h


def tags(data, frame):
    h = header(data)
    if not 0 <= frame < h[4]:
        raise ImportError(f"MD3 frame {frame} outside {h[4]} frames")
    result = {}
    for i in range(h[5]):
        t = TAG.unpack_from(data, h[9] + (frame * h[5] + i) * TAG.size)
        result[t[0].split(b"\0")[0].decode("ascii")] = t[1:]
    return result


def meshes(data):
    h = header(data)
    offset = h[10]
    result = []
    for _ in range(h[6]):
        if offset + MESH.size > len(data):
            raise ImportError("Truncated MD3 mesh header")
        m = list(MESH.unpack_from(data, offset))
        if m[0] != b"IDP3" or m[3] != h[4] or m[-1] < MESH.size or offset + m[-1] > len(data):
            raise ImportError("Invalid MD3 mesh")
        if m[10] + m[3] * m[5] * 8 > m[-1]:
            raise ImportError("Truncated MD3 vertex frames")
        result.append((offset, m))
        offset += m[-1]
    return result


def reverse_animations(data, anims):
    """Append reversed vertex/tag frames for source animations marked Flip."""
    h = header(data)
    frames = list(range(h[4]))
    result = {name: list(values) for name, values in anims.items()}
    for name, values in result.items():
        start, count, _, _, flip, upper, lower, _ = values
        if not flip or not lower or upper:
            continue
        if start < 0 or start + count > h[4]:
            raise ImportError(f"Reversed animation {name} outside MD3")
        values[0] = len(frames)
        frames.extend(reversed(range(start, start + count)))
    frameblock = b"".join(data[h[8] + f * 56:h[8] + (f + 1) * 56] for f in frames)
    tagstride = h[5] * TAG.size
    tagblock = b"".join(data[h[9] + f * tagstride:h[9] + (f + 1) * tagstride] for f in frames)
    meshblock = bytearray()
    for offset, m in meshes(data):
        stride = m[5] * 8
        vertexblock = b"".join(data[offset + m[10] + f * stride:offset + m[10] + (f + 1) * stride] for f in frames)
        tail = data[offset + m[10] + h[4] * stride:offset + m[-1]]
        m[3] = len(frames)
        m[-1] += (len(frames) - h[4]) * stride
        meshblock.extend(MESH.pack(*m) + data[offset + MESH.size:offset + m[10]] + vertexblock + tail)
    h[4] = len(frames)
    h[8] = HEADER.size
    h[9] = h[8] + len(frameblock)
    h[10] = h[9] + len(tagblock)
    h[11] = h[10] + len(meshblock)
    return HEADER.pack(*h) + frameblock + tagblock + meshblock, result


def adapt_tags(data, part):
    """Preserve animated tags and add engine attachment points in each frame."""
    h = header(data)
    additions = {
        "lower": {"tag_waist": (0., 0., 12.)},
        "vesttorso": {"tag_chest": (0., 0., 10.)},
        "head": {"tag_crown": (1., 0., 5.), "tag_camera": (5., 0., 5.)},
        "helmet": {},
    }[part]
    additions = {name: pos for name, pos in additions.items() if name not in tags(data, 0)}
    block = bytearray()
    for frame in range(h[4]):
        current = tags(data, frame)
        for name, values in current.items():
            # Both Q3 and Eclipse's third-person weapons point along local +X.
            # Keep the animated attachment basis: the MD3 loader reflects Y
            # and the body's mdlyaw already aligns it with the actor's aim.
            block.extend(TAG.pack(name.encode("ascii"), *values))
        for name, pos in additions.items():
            block.extend(TAG.pack(name.encode("ascii"), *pos, *IDENTITY))
    extra = h[4] * len(additions) * TAG.size
    h[5] += len(additions)
    h[10] += extra
    h[11] += extra
    return HEADER.pack(*h) + data[HEADER.size:h[9]] + block + data[h[10] - extra:]


def animations(data):
    result = {}
    for line in data.decode("ascii").splitlines():
        match = re.fullmatch(r"\s*([A-Z][A-Z_0-9]+)\s+([\d\s]+)\s*", line.split("//")[0])
        if match:
            numbers = [int(v) for v in match[2].split()]
            if len(numbers) == 8:
                result[match[1]] = numbers
    if not result:
        raise ImportError("No named Urban Terror animations found")
    return result


def skin(data):
    result = {}
    for line in data.decode("ascii").splitlines():
        if "," not in line:
            continue
        mesh, texture = (v.strip() for v in line.split(",", 1))
        if mesh.startswith("tag_") or not texture:
            continue
        # The two bundled Athena hair shaders use a simple alpha-tested map.
        if texture in ("athena_hair_tag_b", "athena_hair_desert_w"):
            texture = "models/players/athena/" + texture.removeprefix("athena_") + ".tga"
        if not re.fullmatch(r"[a-zA-Z0-9_]+", mesh) or not re.fullmatch(r"models/[a-zA-Z0-9_/.-]+\.(tga|jpg|png)", texture) or ".." in texture:
            raise ImportError("Unsupported skin entry")
        result[mesh] = texture
    return result


def animated_config(part, anims, numframes):
    # Resolve patterns here: registering a wildcard followed by a specific
    # MD3 animation adds random variants in the engine, rather than replacing.
    source = (ROOT / "src/game/game.h").read_text()
    block = source.split("static const char * const animnames[] =", 1)[1].split("};", 1)[0]
    names_available = [n for n in re.findall(r'"([^"]*)"', block) if n]
    assigned = {}

    def add(names, source, priority):
        start, count, fps, *_ = anims[source]
        if start < 0 or count < 1 or start + count > numframes:
            raise ImportError(f"Animation {source} outside {numframes} MD3 frames")
        for name in names_available:
            if any(fnmatch.fnmatchcase(name, pattern) for pattern in names.split("|")):
                assigned[name] = (start, count, fps, priority)

    # Register a safe pose for every engine animation first. More specific
    # entries below replace it. Priorities keep legs moving while arms fire.
    add("*", "LEGS_IDLE" if part == "lower" else "TORSO_STAND_RIFLE", 0)
    add("dying", "BOTH_DEATH_CHEST", 4)
    add("dead", "BOTH_DEAD_CHEST", 4)
    add("vault|parkour up", "BOTH_LEDGECLIMB", 3)
    if part == "lower":
        for names, source in [
            ("idle|edit|win|lose", "LEGS_IDLE"),
            ("walk forward|walk left|walk right", "LEGS_WALK"),
            ("walk backward", "LEGS_BACKWALK"),
            ("run forward|run left|run right|sprint", "LEGS_RUN"),
            ("run backward", "LEGS_BACKRUN"),
            ("crouch|power slide", "LEGS_IDLECR"),
            ("crawl forward|crawl left|crawl right", "LEGS_WALKCR"),
            ("crawl backward", "LEGS_BACKWALKCR"),
            ("jump*|boost*|parkour jump|fly kick", "LEGS_JUMP"),
            ("crouch jump*", "LEGS_IDLECR"),
            ("swim|sink", "LEGS_SWIM"),
        ]:
            add(names, source, 1)
    else:
        add("idle|edit|win|lose", "TORSO_STAND_RIFLE", 0)
        add("pistol|pistol power|pistol zoom", "TORSO_STAND_PISTOL", 2)
        add("pistol primary|pistol secondary", "TORSO_ATTACK_PISTOL", 3)
        add("pistol reload", "TORSO_RELOAD_PISTOL", 3)
        for weapon in ("smg", "shotgun", "flamer", "plasma", "zapper", "rifle", "rocket", "minigun", "eclipse"):
            add(f"{weapon}|{weapon} power|{weapon} zoom", "TORSO_STAND_RIFLE", 2)
            add(f"{weapon} primary|{weapon} secondary", "TORSO_ATTACK_RIFLE", 3)
            add(f"{weapon} reload", "TORSO_RELOAD_RIFLE", 3)
        for weapon in ("grenade", "corroder", "mine"):
            add(f"{weapon}|{weapon} power|{weapon} zoom|{weapon} reload", "TORSO_STAND_PISTOL", 2)
            add(f"{weapon} primary|{weapon} secondary", "TORSO_ATTACK_GRENADE", 3)
        add("claw*|sword*|jetsaw*", "TORSO_STAND_KNIFE", 2)
        add("switch|use", "TORSO_WEAPON_RAISE", 3)
        add("swim|sink", "TORSO_SWIM", 1)
    groups = {}
    for name, values in assigned.items():
        groups.setdefault(values, []).append(name)
    return [f'md3anim "{"|".join(names)}" {start} {count} {fps} {priority}'
            for (start, count, fps, priority), names in groups.items()]


def import_pack(source, output):
    assets = Assets(source)
    entries = {}
    manifest = {"format": 1, "source": "Urban Terror 4.3 / FrozenSand",
                "local_only": True, "teams": {"alpha": "swat_w", "omega": "desert_w"}, "models": {}}
    try:
        for actor in ("orion", "athena"):
            base = f"models/players/{actor}"
            anims = animations(assets.read(f"{base}/animation.cfg"))
            modeldata = {}
            lower_anims = None
            for lod in range(3):
                suffix = f"_{lod}" if lod else ""
                for part in ("lower", "vesttorso", "head", "helmet"):
                    data = assets.read(f"{base}/{part}{suffix}.md3")
                    if part == "lower":
                        data, lower_anims = reverse_animations(data, anims)
                    modeldata[part, lod] = data
                    entries[f"{PREFIX}/{actor}/mesh/{part}{suffix}.md3"] = adapt_tags(data, part)
            # The source origin is above the feet. Fit the complete standing
            # silhouette to the existing 21.4-unit actor, before playerscale.
            lower = modeldata["lower", 0]
            floor = struct.unpack_from("<6f", lower, header(lower)[8] + anims["LEGS_IDLE"][0] * 56)[2]
            torso = tags(lower, anims["LEGS_IDLE"][0])["tag_torso"]
            headtag = tags(modeldata["vesttorso", 0], anims["TORSO_STAND_RIFLE"][0])["tag_head"]
            helmet = modeldata["helmet", 0]
            bounds = struct.unpack_from("<6f", helmet, header(helmet)[8])
            corners = [(x, y, z) for x in (bounds[0], bounds[3]) for y in (bounds[1], bounds[4]) for z in (bounds[2], bounds[5])]
            top = max(torso[2] + headtag[2] + sum(headtag[5 + i * 3] * c[i] for i in range(3)) for c in corners)
            scale = 21.4 / (top - floor)
            manifest["models"][actor] = {"scale": scale, "feet_offset": -floor, "standing_height": 21.4}
            for team, style in manifest["teams"].items():
                skins = {part: skin(assets.read(f'{base}/{"vest" if part == "vesttorso" else part}_{style}{"_" if part == "head" else ""}.skin')) for part in ("lower", "vesttorso", "head", "helmet")}
                for lod in range(3):
                    suffix = f"_{lod}" if lod else ""
                    lines = ["// Locally adapted Urban Terror model. Generated; do not redistribute.", f'md3dir "{PREFIX}/{actor}"']
                    for index, part in enumerate(("lower", "vesttorso", "head", "helmet")):
                        lines.append(f'md3load "mesh/{part}{suffix}.md3"')
                        lines.append(f"md3pitch {1 if part == 'vesttorso' else 0}")
                        lines.append('md3alphatest "*" 0')
                        for mesh, texture in skins[part].items():
                            mesh_names = {m[1].split(b"\0")[0].decode("ascii") for _, m in meshes(modeldata[part, lod])}
                            if mesh not in mesh_names:
                                continue
                            png = f"textures/{Path(texture).stem}.png"
                            target = f"{PREFIX}/{actor}/{png}"
                            if target not in entries:
                                image = Image.open(io.BytesIO(assets.read(texture))).convert("RGBA" if mesh == "h_hair" else "RGB")
                                buffer = io.BytesIO()
                                image.save(buffer, format="PNG")
                                entries[target] = buffer.getvalue()
                            lines.append(f'md3skin "{mesh}" "{png}"')
                            if mesh == "h_hair":
                                lines.extend(['md3alphatest "h_hair" 0.5', 'md3cullface "h_hair" 0'])
                        if part in ("lower", "vesttorso"):
                            lines.extend(animated_config(part, lower_anims if part == "lower" else anims, header(modeldata[part, lod])[4]))
                        if index == 1:
                            lines.append('md3link 0 1 "tag_torso"')
                        elif index > 1:
                            lines.append(f'md3link 1 {index} "tag_head"')
                    lines.extend([f"mdlscale {scale * 100:.8f}", f"mdltrans 0 0 {-floor:.8f}", "mdlyaw 90", "mdlcolor 1 1 1", "mdlmaterial 0 0 0", "mdlmixer 0", "mdlspec 20"])
                    if not lod:
                        lines.extend(["mdllod lod1 128", "mdllod lod2 512"])
                    path = f"{PREFIX}/{actor}/{team}" + (f"/lod{lod}" if lod else "")
                    entries[f"{path}/md3.cfg"] = ("\n".join(lines) + "\n").encode()
        manifest["inputs"] = assets.used
        entries[f"{PREFIX}/manifest.json"] = json.dumps(manifest, indent=2).encode()
        entries[f"{PREFIX}/ready.cfg"] = b"// Local Urban Terror soldier pack.\ncsgopensoldiers 1\n"
        entries["URBAN-TERROR-ASSETS.txt"] = b"Urban Terror 4.3 models and textures: FrozenSand and their respective authors.\nLocally adapted from the user's installation; not covered by the Eclipse Recoil\nsource license. This package must not be committed or included in releases\nwithout separate redistribution permission.\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(".zip.tmp")
        try:
            with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as z:
                for name, data in sorted(entries.items()):
                    z.writestr(name, data)
            with zipfile.ZipFile(temp) as z:
                if z.testzip():
                    raise ImportError("Generated ZIP integrity check failed")
            temp.replace(output)
        finally:
            temp.unlink(missing_ok=True)
    finally:
        assets.close()
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installation", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/csgopen/urbanterror-soldiers.zip")
    args = parser.parse_args()
    try:
        manifest = import_pack(args.installation, args.output)
    except (ImportError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Soldier import failed: {error}\n")
    print(f"Imported Orion and Athena, Alpha/Omega uniforms and two LODs: {args.output}")
    print(json.dumps(manifest["models"], indent=2))


if __name__ == "__main__":
    main()
