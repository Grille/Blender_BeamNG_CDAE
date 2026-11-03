import collections
import copy
import glob
import json
import os
import unittest

import bpy

from grille_cdae.common import *
from grille_cdae.beamng.material import Material, MaterialBuilder, MaterialParser, MaterialImportError, ImageNodeMode
from grille_cdae.blender.shader_nodes import BeamBSDF15, BeamBDSF10Basic, BeamImageTex, BeamImageTexConverter, BeamRGBA, BeamStageMix

import grille_cdae.addon as addon
import grille_cdae.beamng.material.material_socket_info as _SI


def setUpModule(): addon.register()
def tearDownModule(): addon.unregister()


# legacy json key -> primary key, legacy keys are written back under their primary key
ALIASES: dict[str, str] = {
    alias: json_key[0]
    for info in vars(_SI).values() if isinstance(info, dict)
    for json_key in cast(dict[str, _SI.JsonKey | None], info).values() if isinstance(json_key, tuple)
    for alias in json_key[1:]
}


# everything the exporter writes for this tree, so import -> export must reproduce it exactly
CANONICAL: SDict = {
    "name": "test_mat", "mapTo": "test_mat", "class": "Material", "version": 1.5,
    "groundType": "METAL",
    "activeLayers": 2,
    "alphaTest": True, "alphaRef": 128,
    "doubleSided": True, "invertBackFaceNormals": True,
    "castShadows": False,
    "subSurface": True, "subSurfaceIntensity": 0.25,
    "translucent": True, "translucentBlendOp": "LerpAlpha", "translucentZWrite": True,
    "cubemap": "global_cubemap",
    "Stages": [
        {
            "baseColorMap": "albedo.png", "diffuseMapUseUV": 1, "baseColorFactor": [1.0, 0.5, 0.0, 1.0], "vertColor": True,
            "normalMap": "normal.png", "normalMapStrength": 0.5,
            "roughnessFactor": 0.75,
            "emissiveFactor": [1.0, 0.0, 0.0],
            "detailMap": "detail.png", "detailBaseColorMapStrength": 0.5, "detailScale": [4.0, 8.0],
            "colorPaletteMap": "palette.png", "paletteMetallic": False,
            "animFlags": 3, "rotSpeed": 0.5, "scrollSpeed": 2.0, "scrollDir": [1.0, 0.0],
        },
        {"metallicFactor": 1.0, "roughnessFactor": 0.3},
        {}, {},
    ],
}

CANONICAL_10: SDict = {
    "name": "test_mat", "mapTo": "test_mat", "class": "Material", "version": 1.0,
    "Stages": [
        {
            "baseColorMap": "albedo.png", "baseColorFactor": [1.0, 0.5, 0.0, 1.0], "instanceDiffuse": True,
            "normalMap": "normal.png",
            "detailMap": "detail.png", "detailScale": [4.0, 4.0],
            "reflectivityMap": "reflect.png", "reflectivityMapFactor": 0.5,
            "overlayMap": "overlay.png",
            "opacityMap": "opacity.png",
            "specularMap": "spec.png", "pixelSpecular": True, "specular": [0.5, 0.5, 0.5, 1.0], "roughnessFactor": 0.25,
            "emissive": True,
            "glow": True, "glowFactor": [1.0, 0.0, 0.0],
        },
        {}, {}, {},
    ],
}



def import_material(raw: SDict, name: str = "test_mat", image_nodes = ImageNodeMode.CONVERTER) -> bpy.types.Material:
    bmat = bpy.data.materials.new(name)
    parser = MaterialParser()
    parser.image_nodes = image_nodes
    parser.parse_to_bmat(Material(copy.deepcopy(raw)), bmat)
    return bmat


def export_material(bmat: bpy.types.Material) -> SDict:
    builder = MaterialBuilder()
    builder.build_from_bmat(bmat)
    return builder.material.value_dict


def cleanup():
    for bmat in list(bpy.data.materials): bpy.data.materials.remove(bmat)
    for image in list(bpy.data.images): bpy.data.images.remove(image)



class MaterialImportTest(unittest.TestCase):

    def tearDown(self):
        cleanup()


    def test_canonical_roundtrip(self):
        for mode in ImageNodeMode:
            with self.subTest(mode):
                self.assertEqual(export_material(import_material(CANONICAL, image_nodes=mode)), CANONICAL)
                cleanup()


    def test_nodes(self):
        bmat = import_material(CANONICAL)
        idnames = collections.Counter(node.bl_idname for node in not_none(bmat.node_tree).nodes)
        self.assertEqual(idnames[BeamBSDF15.bl_idname], 2)
        self.assertEqual(idnames[BeamStageMix.bl_idname], 1)
        self.assertEqual(idnames["ShaderNodeTexImage"], 4)
        self.assertEqual(idnames[BeamImageTexConverter.bl_idname], 1)  # normal, color maps link directly
        self.assertEqual(idnames["ShaderNodeNormalMap"], 0)
        self.assertEqual(not_none(bpy.data.images["albedo.png"].colorspace_settings).name, "Non-Color")


    def test_nodes_beam_image_tex(self):
        bmat = import_material(CANONICAL, image_nodes=ImageNodeMode.BEAM_IMAGE_TEX)
        idnames = collections.Counter(node.bl_idname for node in not_none(bmat.node_tree).nodes)
        self.assertEqual(idnames[BeamImageTex.bl_idname], 4)
        self.assertEqual(idnames["ShaderNodeTexImage"], 0)
        self.assertEqual(idnames[BeamImageTexConverter.bl_idname], 0)


    def test_missing_keys_keep_node_defaults(self):
        bmat = import_material({"name": "m", "version": 1.5, "Stages": [{"roughnessFactor": 0.5}]})
        stage = next(n for n in not_none(bmat.node_tree).nodes if n.bl_idname == BeamBSDF15.bl_idname)
        self.assertAlmostEqual(stage.inputs[BeamBSDF15.Sockets.ROUGHNESS_FACTOR].default_value, 0.5) # pyright: ignore
        self.assertAlmostEqual(stage.inputs[BeamBSDF15.Sockets.METALLIC_FACTOR].default_value, 0.0) # pyright: ignore
        self.assertNotIn("metallicFactor", cast(list[SDict], export_material(bmat)["Stages"])[0])


    def test_canonical_roundtrip_10(self):
        for mode in ImageNodeMode:
            with self.subTest(mode):
                self.assertEqual(export_material(import_material(CANONICAL_10, image_nodes=mode)), CANONICAL_10)
                cleanup()


    def test_nodes_10(self):
        bmat = import_material(CANONICAL_10)
        idnames = collections.Counter(node.bl_idname for node in not_none(bmat.node_tree).nodes)
        self.assertEqual(idnames[BeamBDSF10Basic.bl_idname], 1)
        self.assertEqual(idnames[BeamImageTex.bl_idname], 0)
        self.assertEqual(idnames["ShaderNodeTexImage"], 7)
        self.assertGreaterEqual(idnames[BeamImageTexConverter.bl_idname], 4)  # at least color, detail, reflectivity, overlay (RGBA sockets)
        self.assertEqual(idnames[BeamRGBA.bl_idname], 1)  # color factor


    def test_legacy_keys_10(self):
        legacy = copy.deepcopy(CANONICAL_10)
        stage = cast(list[SDict], legacy["Stages"])[0]
        stage["colorMap"] = stage.pop("baseColorMap")
        stage["diffuseColor"] = stage.pop("baseColorFactor")
        self.assertEqual(export_material(import_material(legacy)), CANONICAL_10)


    def test_missing_version_is_10(self):
        bmat = import_material({"name": "m", "Stages": [{"baseColorMap": "a.png"}]})
        self.assertEqual(export_material(bmat)["version"], 1.0)


    def test_unknown_version(self):
        with self.assertRaises(MaterialImportError):
            import_material({"name": "m", "version": 2.0})



@unittest.skipUnless(os.environ.get("BEAMNG_SAMPLES_DIR"), "pass a BeamNG directory to run_tests.py")
class MaterialSampleRoundtripTest(unittest.TestCase):

    def tearDown(self):
        cleanup()


    def test_import_export_is_stable(self):
        """First export may lose data the node tree can't represent, after that import -> export must be stable."""

        root = os.environ["BEAMNG_SAMPLES_DIR"]
        lost: collections.Counter[str] = collections.Counter()
        count = 0

        for path in glob.glob(os.path.join(root, "**", "*.materials.json"), recursive=True):
            with open(path, encoding="utf-8") as f:
                entries = cast(dict[str, SDict], json.load(f))

            for key, raw in entries.items():
                if raw.get("class") not in ("Material", "material"):
                    continue

                with self.subTest(file=os.path.relpath(path, root), material=key):
                    first = export_material(import_material(raw, "rt"))
                    cleanup()
                    second = export_material(import_material(first, "rt"))
                    cleanup()
                    self.assertEqual(second, first)
                    count += 1

                    lost.update(k for k in raw if k not in first and k != "Stages")
                    layers = int(cast(int, raw.get("activeLayers", 1)) or 1)
                    stages = zip(cast(list[SDict], raw.get("Stages", [])), cast(list[SDict], first["Stages"]))
                    for stage, exported in list(stages)[:layers]:
                        lost.update(f"Stages.{k}" for k in stage if ALIASES.get(k, k) not in exported)

        self.assertGreater(count, 0)
        print(f"\n  {count} materials, keys lost on first import -> export:")
        for key, n in lost.most_common(25): print(f"    {n:5} {key}")
