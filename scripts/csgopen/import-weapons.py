#!/usr/bin/env python3
"""Import local Urban Terror weapons as native first/third-person MD3 models.

Only mesh, image, skin and named animation data are read. Source configuration
files are never executed. The resulting ZIP is tracked and included in client
releases, like the soldier pack.
"""

import argparse
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import zipfile

from PIL import Image


spec = importlib.util.spec_from_file_location("soldiers", Path(__file__).with_name("import-soldiers.py"))
soldiers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(soldiers)
ROOT = soldiers.ROOT
PREFIX = "weapons/urbanterror"
# Appearance only: the server's original weapon names, ammunition and rules stay.
MAPPING = {
    "pistol": ("deserteagle", "deagle"),
    "smg": ("mp5k", "mp5k"),
    "plasma": ("mac11", "mac11"),
    "zapper": ("ak103", "ak103"),
    "rifle": ("sr8", "sr8"),
    "flamer": ("psg1", "psg1"),
    "shotgun": ("spas12", "spas12"),
    "minigun": ("negev", "negev"),
    "grenade": ("grenade", "grenade"),
    "corroder": ("grenade", "grenade"),
    "rocket": ("hk69", "hk69"),
}


def clean(data):
    text = data.decode("ascii")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def animations(data, frames):
    result = {}
    for line in clean(data).splitlines():
        match = re.fullmatch(r"\s*WEAPON_([A-Z_]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*", line)
        if match:
            start, count, fps, loop = map(int, match.groups()[1:])
            if count < 1 or fps < 1 or start + count > frames:
                raise soldiers.ImportError(f"Animation {match[1]} outside {frames} MD3 frames")
            result[match[1]] = (start, count, fps, loop)
    if not {"IDLE", "FIRE"} <= result.keys():
        raise soldiers.ImportError("Missing weapon idle/fire animation")
    return result


def animation_config(weapon, anims):
    # Source FPS affect appearance only; weapon timers still come from the server.
    result = []
    for names, source in [
        (f"idle|switch|use|vault|{weapon}|{weapon} zoom", "IDLE"),
        (f"{weapon} primary|{weapon} secondary", "FIRE"),
        (f"{weapon} reload", "RELOAD" if "RELOAD" in anims else "IDLE"),
        (f"{weapon} power", "READY_FIRE" if "READY_FIRE" in anims else "IDLE"),
    ]:
        start, count, fps, _ = anims[source]
        result.append(f'md3anim "{names}" {start} {count} {fps} 1')
    return result


def complete_actions(anims):
    # SR8's fire and bolt action are one contiguous shot cycle. The shotgun's
    # insertion has separate start/end entries but the game reloads a clip.
    for action, tail in (("FIRE", "BOLT"), ("RELOAD_START", "RELOAD_END")):
        if action in anims and tail in anims:
            start, _, fps, loop = anims[action]
            end = anims[tail][0] + anims[tail][1]
            if end > start:
                anims["RELOAD" if action == "RELOAD_START" else action] = (start, end - start, fps, loop)
    return anims


def adapt_tags(data):
    """Add native aliases and emulate Q3's normalization of attachment axes."""
    h = soldiers.header(data)
    initial = soldiers.tags(data, 0)
    aliases = {"tag_muzzle": "tag_flash", "tag_eject": "tag_ejector"}
    additions = {n: source for n, source in aliases.items() if n not in initial and source in initial}
    if "tag_weapon" not in initial:
        additions["tag_weapon"] = None
    if "tag_muzzle" not in initial and "tag_muzzle" not in additions:
        additions["tag_muzzle"] = "tag_main" if "tag_main" in initial else "tag_weapon"
    block = bytearray()
    for frame in range(h[4]):
        current = soldiers.tags(data, frame)
        # Q3's MD3 tag interpolation normalizes each axis. Several source
        # holds store a 3.7056 scale in those axes even though their linked
        # meshes already contain that scale. The native loader keeps matrix
        # scale, so normalize here to avoid enlarging the weapon a second time.
        for name, values in current.items():
            axes = []
            for i in range(3):
                axis = values[3 + i*3:6 + i*3]
                length = math.sqrt(sum(v*v for v in axis))
                if length < 1e-6:
                    raise soldiers.ImportError(f"Degenerate weapon tag: {name}")
                axes.extend(v / length for v in axis)
            current[name] = (*values[:3], *axes)
        for name, values in current.items():
            block.extend(soldiers.TAG.pack(name.encode("ascii"), *values))
        for name, source in additions.items():
            values = current[source] if source in current else (0., 0., 0., *soldiers.IDENTITY)
            block.extend(soldiers.TAG.pack(name.encode("ascii"), *values))
    # Some source holds (MAC-11) repeat tag names. The parsed tag table
    # resolves these once; calculate offsets from the actual rebuilt block.
    extra = len(block) - (h[10] - h[9])
    h[5] = len(initial) + len(additions)
    h[10] += extra
    h[11] += extra
    return soldiers.HEADER.pack(*h) + data[soldiers.HEADER.size:h[9]] + block + data[h[10] - extra:]


def skin(data):
    result = {}
    for line in clean(data).splitlines():
        if "," not in line:
            continue
        name, texture = (v.strip() for v in line.split(",", 1))
        if name and texture and not name.startswith("tag_"):
            result[name] = texture
    return result


def attachment_tag(suffix, parttags, roottags):
    # A part can expose tag_main as well as its own attachment (SPAS ejector).
    # Prefer the named moving part rather than the first shared tag.
    expected = f"tag_{suffix}"
    if expected in roottags:
        return expected
    return next((tag for tag in parttags if tag in roottags), expected)


class Importer:
    def __init__(self, source):
        self.assets = soldiers.Assets(source)
        self.files = {n.replace("\\", "/").lower(): n for n in self.assets.files}
        self.entries = {}

    def path(self, name):
        name = name.replace("\\", "/")
        if not re.fullmatch(r"models/[a-zA-Z0-9_./-]+", name) or ".." in name:
            raise soldiers.ImportError(f"Unsupported asset path: {name}")
        if name.lower() not in self.files:
            raise soldiers.ImportError(f"Missing Urban Terror asset: {name}")
        return self.files[name.lower()]

    def read(self, name):
        return self.assets.read(self.path(name))

    def texture(self, name):
        name = name.replace("\\", "/")
        stem = name.rsplit(".", 1)[0] if Path(name).suffix else name
        candidates = [name] + [stem + ext for ext in (".tga", ".jpg", ".png")]
        actual = next((self.path(n) for n in candidates if n.lower() in self.files), None)
        if actual is None:
            raise soldiers.ImportError(f"Unresolved weapon texture: {name}")
        target = "textures/" + actual.removeprefix("models/weapons2/").rsplit(".", 1)[0].lower() + ".png"
        key = PREFIX + "/" + target
        if key not in self.entries:
            # The selected weapon skins are opaque; source alpha often stores a
            # specular mask rather than transparency.
            img = Image.open(io.BytesIO(self.assets.read(actual))).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            self.entries[key] = buf.getvalue()
        return target

    def model(self, name, override=None, aliases=False):
        data = self.read(name)
        if aliases:
            data = adapt_tags(data)
        data = bytearray(data)
        skins = []
        for index, (offset, msh) in enumerate(soldiers.meshes(data)):
            meshname = msh[1].split(b"\0")[0].decode("ascii")
            shader = bytes(data[offset + msh[8]:offset + msh[8] + 64]).split(b"\0")[0].decode("ascii") if msh[4] else ""
            texture = (override or {}).get(meshname, shader)
            # Duplicate names in source MD3s may have different skins. Native
            # md3skin matches names, so give every exported surface a unique ID.
            unique = f"surface_{index}"
            msh[1] = unique.encode("ascii")
            soldiers.MESH.pack_into(data, offset, *msh)
            skins.append((unique, self.texture(texture)))
        target = "mesh/" + name.removeprefix("models/weapons2/").lower()
        self.entries[PREFIX + "/" + target] = bytes(data)
        return target, skins, bytes(data)

    @staticmethod
    def load(target, skins, pitch=0):
        return [f'md3load "{target}"', f"md3pitch {pitch}", 'md3alphatest "*" 0'] + [f'md3skin "{mesh}" "{texture}"' for mesh, texture in skins]

    def config(self, name, lines, view=False):
        # World meshes and character meshes share source units. First-person
        # holds are authored at the camera origin, with their own tag scales.
        # Flying grenades need a readable silhouette, independently of the
        # hand-held mesh and the server's collision radius.
        scale = 100 if name.endswith("/proj") else (27 if view else 31)
        lines += [f"mdlscale {scale}", *(["mdlyaw 90"] if view else []), "mdlcolor 1 1 1", "mdlmaterial 0 0 0", "mdlmixer 0", "mdlspec 35"]
        self.entries[f"{PREFIX}/{name}/md3.cfg"] = ("\n".join(lines) + "\n").encode()

    def weapon(self, weapon, folder, stem):
        base = f"models/weapons2/{folder}"
        grenade = "smoke" if weapon == "corroder" else "he"
        override = skin(self.read(f"{base}/grenade_{grenade}.skin")) if folder == "grenade" else {}
        world, worldskins, worlddata = self.model(f"{base}/{stem}.md3", override, True)
        self.config(weapon + "/vwep", [f'md3dir "{PREFIX}"'] + self.load(world, worldskins))
        if folder == "grenade":
            self.config(weapon + "/proj", [f'md3dir "{PREFIX}"'] + self.load(world, worldskins))
        # The hold mesh contains the animated hands, and its tags drive the
        # bolt, magazine, trigger and other separate first-person pieces.
        holddata = self.read(f"{base}/{stem}_hold.md3")
        anims = complete_actions(animations(self.read(f"{base}/animation.cfg"), soldiers.header(holddata)[4]))
        roottags = soldiers.tags(holddata, 0)
        parts = []
        for name in sorted(self.files.values()):
            if not name.lower().startswith(f"{base}/{stem}_view_".lower()) or not name.lower().endswith(".md3"):
                continue
            raw = self.assets.read(name)
            # Some optional source parts contain tags but no geometry.
            h = soldiers.HEADER.unpack_from(raw)
            if h[6] == 0:
                continue
            soldiers.header(raw)
            suffix = Path(name).stem.lower().split("_view_", 1)[1]
            targets = [f"tag_bul{i:02}" for i in range(1, 11)] if folder == "negev" and suffix == "bullet" else ["tag_main"] if suffix == "main" else [attachment_tag(suffix, soldiers.tags(raw, 0), roottags)]
            if not all(t in roottags for t in targets):
                continue
            partoverride = skin(self.read(f"{base}/grenade_view_main_{grenade}.skin")) if folder == "grenade" and suffix == "main" else {}
            part, partskins, _ = self.model(name.replace("\\", "/"), partoverride)
            parts.extend((part, partskins, tag) for tag in targets)
        if not any(tag == "tag_main" for _, _, tag in parts):
            raise soldiers.ImportError(f"Missing first-person main body for {weapon}")
        for team, style in (("alpha", "swat"), ("omega", "desert")):
            hands = skin(self.read(f"models/weapons2/handskins/hand_{style}.skin"))
            hold, holdskins, _ = self.model(f"{base}/{stem}_hold.md3", hands, True)
            lines = [f'md3dir "{PREFIX}"'] + self.load(hold, holdskins, 1) + animation_config("grenade" if weapon == "corroder" else weapon, anims)
            for index, (part, partskins, tag) in enumerate(parts, 1):
                lines += self.load(part, partskins) + [f'md3link 0 {index} "{tag}"']
            self.config(f"{weapon}/hwep/{team}", lines, True)
        return {"source": folder, "stem": stem, "frames": soldiers.header(holddata)[4], "linked_parts": len(parts), "animations": anims}

    def icon(self, weapon, stem):
        name = f"icons/weapons_mono/{stem}.tga"
        actual = self.files.get(name)
        if actual is None:
            raise soldiers.ImportError(f"Missing weapon icon: {name}")
        img = Image.open(io.BytesIO(self.assets.read(actual))).convert("RGBA")
        # The UI uses square slots; pad rather than stretch wide silhouettes.
        size = max(img.size)
        canvas = Image.new("RGBA", (size, size))
        canvas.paste(img, ((size-img.width)//2, (size-img.height)//2))
        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        self.entries[f"{PREFIX}/icons/{weapon}.png"] = buf.getvalue()


def import_pack(source, output):
    importer = Importer(source)
    try:
        manifest = {"format": 1, "source": "Urban Terror 4.3 / FrozenSand", "bundled": True,
                    "models": {weapon: importer.weapon(weapon, *source) for weapon, source in MAPPING.items()},
                    "inputs": importer.assets.used}
        for weapon, (folder, _) in MAPPING.items():
            importer.icon(weapon, "grenade_smoke" if weapon == "corroder" else "grenade_he" if weapon == "grenade" else folder)
        importer.entries[f"{PREFIX}/manifest.json"] = json.dumps(manifest, indent=2).encode()
        ready = ["// Local Urban Terror weapon pack.", "csgopenweaponmodels 1", "csgopenweaponicons 1"]
        for weapon, model in manifest["models"].items():
            anims = model["animations"]
            fire = anims["FIRE"][1] * 1000 / anims["FIRE"][2]
            reload = anims.get("RELOAD", anims["IDLE"])
            reload = reload[1] * 1000 / reload[2]
            ready.append(f"csgopenweaponanim $W_{weapon.upper()} {fire:.6f} {reload:.6f}")
        importer.entries[f"{PREFIX}/ready.cfg"] = ("\n".join(ready) + "\n").encode()
        importer.entries["URBAN-TERROR-WEAPONS.txt"] = b"Urban Terror 4.3 models and textures: FrozenSand and their respective authors.\nLocally adapted from the user's installation; not covered by the Eclipse Recoil\nsource license. Do not commit or redistribute this package without permission.\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(".zip.tmp")
        try:
            with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as z:
                for name, data in sorted(importer.entries.items()):
                    z.writestr(name, data)
            with zipfile.ZipFile(temp) as z:
                if z.testzip():
                    raise soldiers.ImportError("Generated ZIP integrity check failed")
            temp.replace(output)
        finally:
            temp.unlink(missing_ok=True)
        return manifest
    finally:
        importer.assets.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installation", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/csgopen/weapons.zip")
    args = parser.parse_args()
    try:
        manifest = import_pack(args.installation, args.output)
    except (soldiers.ImportError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Weapon import failed: {error}\n")
    print(f'Imported {len(manifest["models"])} weapon appearances: {args.output}')


if __name__ == "__main__":
    main()
