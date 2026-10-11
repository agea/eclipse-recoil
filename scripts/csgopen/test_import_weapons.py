import importlib.util
import io
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from PIL import Image


spec = importlib.util.spec_from_file_location("weapons", Path(__file__).with_name("import-weapons.py"))
weapons = importlib.util.module_from_spec(spec)
spec.loader.exec_module(weapons)
md3 = weapons.soldiers


def fixture():
    frames = b"".join(struct.pack("<10f16s", *([float(i)] * 10), b"frame") for i in range(2))
    tags = b"".join(md3.TAG.pack(b"tag_flash", float(i), 2., 3., *md3.IDENTITY) for i in range(2))
    surfaces = b""
    for texture in (b"models/weapons2/test/ONE.JPG", b"models\\weapons2\\test\\two.tga"):
        surfaces += md3.MESH.pack(b"IDP3", b"duplicate", 0, 2, 1, 1, 1, 108, 120, 188, 196, 212)
        surfaces += struct.pack("<3i64si2f8h", 0, 0, 0, texture, 0, 0., 0., *([0] * 8))
    h = md3.HEADER.pack(b"IDP3", 15, b"fixture", 0, 2, 1, 2, 0, 108, 108 + len(frames), 108 + len(frames) + len(tags), 108 + len(frames) + len(tags) + len(surfaces))
    return h + frames + tags + surfaces


class WeaponImportChecks(unittest.TestCase):
    def test_weapon_icon_preserves_transparency_and_aspect_ratio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            buf = io.BytesIO()
            Image.new("RGBA", (8, 4), (255, 255, 255, 128)).save(buf, format="PNG")
            with zipfile.ZipFile(root / "test.pk3", "w") as z:
                z.writestr("icons/weapons_mono/spas12.tga", buf.getvalue())
            importer = weapons.Importer(root)
            try:
                importer.icon("shotgun", "spas12")
                icon = Image.open(io.BytesIO(importer.entries[weapons.PREFIX + "/icons/shotgun.png"]))
                self.assertEqual(icon.size, (8, 8))
                self.assertEqual(icon.getpixel((0, 0))[3], 0)
                self.assertEqual(icon.getpixel((0, 2)), (255, 255, 255, 128))
            finally:
                importer.assets.close()

    def test_moving_part_prefers_named_attachment_over_shared_main(self):
        tags = {"tag_main": (), "tag_ejector": ()}
        self.assertEqual(weapons.attachment_tag("ejector", tags, tags), "tag_ejector")
        self.assertEqual(weapons.attachment_tag("slide", {"tag_slide": ()}, {"tag_slide": ()}), "tag_slide")
        self.assertEqual(weapons.attachment_tag("other", {"tag_link": ()}, {"tag_link": ()}), "tag_link")

    def test_duplicate_source_tags_rebuild_valid_offsets(self):
        original = fixture()
        h = md3.header(original)
        block = b"".join(original[h[9] + i * md3.TAG.size:h[9] + (i+1) * md3.TAG.size] * 2 for i in range(h[4]))
        extra = len(block) - (h[10] - h[9])
        h[5] = 2
        h[10] += extra
        h[11] += extra
        repeated = md3.HEADER.pack(*h) + original[md3.HEADER.size:h[9]] + block + original[h[10]-extra:]
        adapted = weapons.adapt_tags(repeated)
        new = md3.header(adapted)
        self.assertEqual(len(md3.meshes(adapted)), 2)
        self.assertEqual(original[md3.header(original)[10]:], adapted[new[10]:])
        self.assertEqual(md3.tags(adapted, 1)["tag_muzzle"], md3.tags(original, 1)["tag_flash"])

    def test_baked_tag_scale_is_removed_without_rotating_or_moving_it(self):
        data = bytearray(fixture())
        h = md3.header(data)
        basis = (0., 3.7, 0., -3.7, 0., 0., 0., 0., 3.7)
        for frame in range(h[4]):
            md3.TAG.pack_into(data, h[9] + frame * md3.TAG.size, b"tag_flash", float(frame), 2., 3., *basis)
        adapted = weapons.adapt_tags(data)
        for frame in range(h[4]):
            self.assertEqual(md3.tags(adapted, frame)["tag_muzzle"], (float(frame), 2., 3., 0., 1., 0., -1., 0., 0., 0., 0., 1.))

    def test_full_bolt_and_reload_sequences_are_contiguous(self):
        anims = {"IDLE": (0, 1, 10, 1), "FIRE": (0, 16, 40, 0), "BOLT": (15, 51, 35, 0),
                 "RELOAD_START": (27, 8, 15, 0), "RELOAD": (35, 8, 24, 0), "RELOAD_END": (43, 14, 15, 0)}
        result = weapons.complete_actions(anims)
        self.assertEqual(result["FIRE"], (0, 66, 40, 0))
        self.assertEqual(result["RELOAD"], (27, 30, 15, 0))

    def test_aliases_preserve_animated_basis_and_surface_bytes(self):
        original = fixture()
        adapted = weapons.adapt_tags(original)
        old, new = md3.header(original), md3.header(adapted)
        self.assertEqual(original[old[10]:], adapted[new[10]:])
        for frame in range(old[4]):
            current = md3.tags(adapted, frame)
            self.assertEqual(current["tag_muzzle"], md3.tags(original, frame)["tag_flash"])
            self.assertEqual(current["tag_weapon"], (0., 0., 0., *md3.IDENTITY))

    def test_named_animation_parser_ignores_comments_and_includes(self):
        data = b'#include "animdef.h"\nWEAPON_IDLE 0 1 10 1\nWEAPON_FIRE 1 1 30 0\n/* WEAPON_FIRE 1000 40 20 0 */\nexec malicious.cfg\n'
        self.assertEqual(weapons.animations(data, 2)["FIRE"], (1, 1, 30, 0))
        with self.assertRaises(md3.ImportError):
            weapons.animations(b'WEAPON_IDLE 0 1 10 1\nWEAPON_FIRE 1 20 30 0', 2)

    def test_duplicate_surface_names_and_texture_case_extensions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            buf = io.BytesIO()
            Image.new("RGB", (2, 2), "blue").save(buf, format="PNG")
            with zipfile.ZipFile(root / "test.pk3", "w") as z:
                z.writestr("models/weapons2/test/hold.MD3", fixture())
                z.writestr("models/weapons2/test/one.jpg", buf.getvalue())
                # Source skins sometimes specify .tga for a .jpg texture.
                z.writestr("models/weapons2/test/TWO.JPG", buf.getvalue())
            importer = weapons.Importer(root)
            try:
                _, skins, data = importer.model("models/weapons2/test/HOLD.md3")
                self.assertEqual([name for name, _ in skins], ["surface_0", "surface_1"])
                self.assertNotEqual(skins[0][1], skins[1][1])
                self.assertEqual([m[1].rstrip(b"\0") for _, m in md3.meshes(data)], [b"surface_0", b"surface_1"])
                with self.assertRaises(md3.ImportError):
                    importer.path("models/../../secret")
            finally:
                importer.assets.close()

    def test_failed_import_preserves_installed_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "weapons.zip"
            output.write_bytes(b"working pack")
            with self.assertRaises(md3.ImportError):
                weapons.import_pack(root, output)
            self.assertEqual(output.read_bytes(), b"working pack")


if __name__ == "__main__":
    unittest.main()
