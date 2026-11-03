import glob
import json
import os
import tempfile
import unittest

from grille_cdae.common import *
from grille_cdae.beamng.material import Material, MaterialLibary
from grille_cdae.beamng.material.material import MaterialStage



class MaterialDictTest(unittest.TestCase):

    def test_construct_empty(self):
        mat = Material({})
        self.assertEqual(len(mat.stages), 4)
        self.assertEqual(mat.value_dict["Stages"], [{}, {}, {}, {}])


    def test_default_value_removes_key(self):
        raw: SDict = {}
        stage = MaterialStage(raw)

        stage.use_anisotropic = True  # default on an absent key
        self.assertNotIn("useAnisotropic", raw)

        stage.use_anisotropic = False
        self.assertEqual(raw["useAnisotropic"], False)

        stage.use_anisotropic = True
        self.assertNotIn("useAnisotropic", raw)

        stage.use_anisotropic = None
        self.assertNotIn("useAnisotropic", raw)


    def test_socket_keys(self):
        raw: SDict = {}
        stage = MaterialStage(raw)
        stage.color.map = "a.png"
        stage.color.vertex_enabled = True
        stage.metallic.factor = 0.25
        stage.detail.normal.strength = 0.5
        stage.clear_coat.roughness = 0.3
        self.assertEqual(raw, {
            "baseColorMap": "a.png",
            "vertColor": True,
            "metallicFactor": 0.25,
            "detailNormalMapStrength": 0.5,
            "clearCoatRoughnessFactor": 0.3,
        })
        self.assertEqual(stage.metallic.factor, 0.25)
        self.assertEqual(stage.roughness.factor, -1)


    def test_legacy_key_aliases(self):
        raw: SDict = {"colorMap": "old.png", "diffuseColor": [1.0, 0.0, 0.0, 1.0]}
        stage = MaterialStage(raw)
        self.assertEqual(stage.color.map, "old.png")
        self.assertEqual(stage.color.factor, Color4F(1.0, 0.0, 0.0, 1.0))

        stage.color.map = "new.png"  # written to the primary key, alias dropped
        self.assertEqual(raw, {"baseColorMap": "new.png", "diffuseColor": [1.0, 0.0, 0.0, 1.0]})

        stage.color.factor = Color4F.WHITE  # default removes primary and alias
        self.assertEqual(raw, {"baseColorMap": "new.png"})


    def test_primary_key_wins_over_alias(self):
        stage = MaterialStage({"baseColorMap": "new.png", "colorMap": "old.png"})
        self.assertEqual(stage.color.map, "new.png")


    def test_unknown_attributes_raise(self):
        mat = Material({})
        stage = mat.stages[0]
        for obj in (mat, mat.translucent, stage, stage.detail, stage.animation, stage.color, stage.ambient_occlusion):
            with self.subTest(type(obj).__name__):
                with self.assertRaises(AttributeError):
                    obj.not_a_field = 1 # pyright: ignore[reportAttributeAccessIssue]


    def test_key_not_valid_for_socket(self):
        stage = MaterialStage({})
        with self.assertRaises(KeyError):
            stage.ambient_occlusion["value"] = 1.0



class MaterialLibaryTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "main.materials.json")


    def tearDown(self):
        self.dir.cleanup()


    def write(self, data: object):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f)


    def read(self) -> object:
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)


    def test_untouched_entries_are_preserved(self):
        original = {
            "existing": {"name": "existing", "class": "Material", "Stages": [{"baseColorMap": "ä.png"}], "customKey": 1},
            "cubemap": {"name": "cubemap", "class": "CubemapData", "cubeFace": ["a", "b"]},
        }
        self.write(original)

        lib = MaterialLibary()
        self.assertTrue(lib.try_load(self.path))
        self.assertTrue("existing" in lib.materials)

        new = Material({})
        new.name = "new"
        lib.set_material(new)
        lib.save(self.path)

        saved = cast(dict[str, object], self.read())
        self.assertEqual(saved["existing"], original["existing"])
        self.assertEqual(saved["cubemap"], original["cubemap"])
        self.assertEqual(cast(SDict, saved["new"])["name"], "new")


    def test_get_material(self):
        self.write({"m": {"name": "m", "Stages": [{"roughnessFactor": 0.5}]}})
        lib = MaterialLibary()
        lib.load(self.path)
        mat = not_none(lib.get_material("m"))
        self.assertEqual(mat.stages[0].roughness.factor, 0.5)
        self.assertIsNone(lib.get_material("missing"))


    def test_missing_file(self):
        self.assertFalse(MaterialLibary().try_load(os.path.join(self.dir.name, "missing.json")))


    def test_invalid_file_raises(self):
        # must not be treated like a missing file, the file would get overwritten on save
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{ invalid")
        with self.assertRaises(ValueError):
            MaterialLibary().try_load(self.path)



@unittest.skipUnless(os.environ.get("BEAMNG_SAMPLES_DIR"), "pass a BeamNG directory to run_tests.py")
class MaterialSampleFilesTest(unittest.TestCase):

    def test_load_save_unchanged(self):
        root = os.environ["BEAMNG_SAMPLES_DIR"]
        files = glob.glob(os.path.join(root, "**", "*.materials.json"), recursive=True)
        self.assertTrue(files, f"no .materials.json files in {root}")

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.json")
            for path in files:
                with self.subTest(file=os.path.relpath(path, root)):
                    with open(path, encoding="utf-8") as f:
                        original = json.load(f)

                    lib = MaterialLibary()
                    lib.load(path)
                    lib.save(out)
                    with open(out, encoding="utf-8") as f:
                        self.assertEqual(json.load(f), original)

                    for name, raw in original.items():
                        if raw.get("class") in ("Material", "material"):
                            mat = not_none(lib.get_material(name))
                            mat.version
                            mat.translucent.blend_mode
                            for stage in mat.stages:
                                stage.color.factor
                                stage.detail.scale
                                stage.animation.flags
