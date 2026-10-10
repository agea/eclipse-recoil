import importlib.util
from pathlib import Path
import struct
import re
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("soldiers", Path(__file__).with_name("import-soldiers.py"))
soldiers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(soldiers)


def fixture():
    frames = 4
    frameblock = b"".join(struct.pack("<10f16s", *([float(i)] * 10), b"frame") for i in range(frames))
    tagblock = b"".join(soldiers.TAG.pack(b"tag_weapon", float(i), 2., 3., *soldiers.IDENTITY) for i in range(frames))
    meshheader = soldiers.MESH.pack(b"IDP3", b"body", 0, frames, 0, 1, 1,
                                    108, 120, 120, 128, 160)
    meshblock = meshheader + struct.pack("<3i2f", 0, 0, 0, 0., 0.) + b"".join(struct.pack("<4h", i, i + 1, i + 2, 0) for i in range(frames))
    h = soldiers.HEADER.pack(b"IDP3", 15, b"fixture", 0, frames, 1, 1, 0,
                              108, 108 + len(frameblock), 108 + len(frameblock) + len(tagblock),
                              108 + len(frameblock) + len(tagblock) + len(meshblock))
    return h + frameblock + tagblock + meshblock


class SoldierImportChecks(unittest.TestCase):
    def test_attachment_basis_and_animated_positions_preserve_mesh_bytes(self):
        original = fixture()
        adapted = soldiers.adapt_tags(original, "vesttorso")
        old, new = soldiers.header(original), soldiers.header(adapted)
        self.assertEqual(original[old[10]:], adapted[new[10]:])
        self.assertEqual(old[4], new[4])
        for frame in range(old[4]):
            tag = soldiers.tags(adapted, frame)["tag_weapon"]
            self.assertEqual(tag[:3], (float(frame), 2., 3.))
            self.assertEqual(tag, soldiers.tags(original, frame)["tag_weapon"])
            self.assertEqual(soldiers.tags(adapted, frame)["tag_chest"][:3], (0., 0., 10.))

    def test_weapon_attachment_preserves_nontrivial_animated_axes(self):
        data = bytearray(fixture())
        h = soldiers.header(data)
        # A different rotation in each frame must survive, including pitch.
        rotations = [soldiers.IDENTITY, (0., 1., 0., -1., 0., 0., 0., 0., 1.),
                     (0., 0., 1., 0., 1., 0., -1., 0., 0.),
                     (-1., 0., 0., 0., -1., 0., 0., 0., 1.)]
        for frame, axes in enumerate(rotations):
            soldiers.TAG.pack_into(data, h[9] + frame * soldiers.TAG.size,
                                  b"tag_weapon", float(frame), 2., 3., *axes)
        adapted = soldiers.adapt_tags(bytes(data), "vesttorso")
        for frame in range(h[4]):
            self.assertEqual(soldiers.tags(adapted, frame)["tag_weapon"],
                             soldiers.tags(bytes(data), frame)["tag_weapon"])

    def test_reverse_walk_keeps_vertex_and_attachment_frames_synchronized(self):
        original = fixture()
        anims = {"LEGS_BACKWALK": [1, 3, 30, 3, 1, 0, 1, 1]}
        data, mapped = soldiers.reverse_animations(original, anims)
        h = soldiers.header(data)
        self.assertEqual(h[4], 7)
        self.assertEqual(mapped["LEGS_BACKWALK"][0], 4)
        self.assertEqual(anims["LEGS_BACKWALK"][0], 1)
        offset, mesh = soldiers.meshes(data)[0]
        for index, expected in enumerate([0, 1, 2, 3, 3, 2, 1]):
            self.assertEqual(soldiers.tags(data, index)["tag_weapon"][0], expected)
            self.assertEqual(struct.unpack_from("<h", data, offset + mesh[10] + index * 8)[0], expected)

    def test_truncated_model_and_invalid_offsets_rejected(self):
        data = fixture()
        for invalid in (data[:80], data[:-1], b"NOPE" + data[4:]):
            with self.assertRaises(soldiers.ImportError):
                soldiers.header(invalid)

    def test_skin_and_named_animations_are_data_not_executable(self):
        parsed = soldiers.skin(b'tag_head,\nh_hair,athena_hair_desert_w\n')
        self.assertEqual(parsed, {"h_hair": "models/players/athena/hair_desert_w.tga"})
        with self.assertRaises(soldiers.ImportError):
            soldiers.skin(b'body,models/../../secret.tga\n')
        parsed = soldiers.animations(b'#include "ignore.h"\nLEGS_IDLE 1 1 15 1 0 0 1 1\nexec malicious.cfg\n')
        self.assertEqual(list(parsed), ["LEGS_IDLE"])

    def test_failed_import_does_not_replace_installed_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "soldiers.zip"
            output.write_bytes(b"previous working pack")
            with self.assertRaises(soldiers.ImportError):
                soldiers.import_pack(root, output)
            self.assertEqual(output.read_bytes(), b"previous working pack")

    def test_movement_and_weapon_mappings_have_no_random_pose_variants(self):
        source_names = """LEGS_IDLE LEGS_WALK LEGS_BACKWALK LEGS_RUN LEGS_BACKRUN
            LEGS_IDLECR LEGS_WALKCR LEGS_BACKWALKCR LEGS_JUMP LEGS_SWIM
            BOTH_DEATH_CHEST BOTH_DEAD_CHEST BOTH_LEDGECLIMB TORSO_STAND_RIFLE
            TORSO_STAND_PISTOL TORSO_ATTACK_PISTOL TORSO_RELOAD_PISTOL
            TORSO_ATTACK_RIFLE TORSO_RELOAD_RIFLE TORSO_ATTACK_GRENADE
            TORSO_STAND_KNIFE TORSO_WEAPON_RAISE TORSO_SWIM""".split()
        anims = {name: [index * 3, 3, 30, 3, 0, 1, 1, 1]
                 for index, name in enumerate(source_names)}
        for part in ("lower", "vesttorso"):
            declarations = soldiers.animated_config(part, anims, 100)
            mapped = {}
            for line in declarations:
                match = re.fullmatch(r'md3anim "([^"]+)" (\d+) (\d+) (\d+) (\d+)', line)
                for name in match[1].split("|"):
                    self.assertNotIn(name, mapped)
                    mapped[name] = int(match[5])
            self.assertGreater(mapped["dying"], mapped["run forward"])
            if part == "lower":
                self.assertGreater(mapped["run forward"], mapped["smg primary"])
            else:
                self.assertGreater(mapped["smg primary"], mapped["run forward"])


if __name__ == "__main__":
    unittest.main()
