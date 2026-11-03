import collections
import unittest

import bpy

from grille_cdae.common import *
from grille_cdae.beamng.material import MaterialBuilder, MaterialParser, MaterialVersion
from grille_cdae.blender.shader_nodes import BeamBSDF15, BeamBDSF10Basic, BeamMaterial, BeamRGBA

import grille_cdae.addon as addon


def setUpModule(): addon.register()
def tearDownModule(): addon.unregister()



class MaterialConvertTest(unittest.TestCase):
    """Blender's Principled / Diffuse BSDF converted to BeamNG nodes (single stage)."""

    def setUp(self):
        self.bmat = bpy.data.materials.new("conv")
        self.tree = not_none(self.bmat.node_tree)
        self.tree.nodes.clear()
        self.output = self.tree.nodes.new("ShaderNodeOutputMaterial")


    def tearDown(self):
        for bmat in list(bpy.data.materials): bpy.data.materials.remove(bmat)
        for image in list(bpy.data.images): bpy.data.images.remove(image)


    def shader(self, idname: str):
        node = self.tree.nodes.new(idname)
        self.tree.links.new(node.outputs[0], self.output.inputs["Surface"])
        return node


    def image(self, name: str):
        node = cast(bpy.types.ShaderNodeTexImage, self.tree.nodes.new("ShaderNodeTexImage"))
        node.image = bpy.data.images.new(name, 4, 4)
        return node


    def convert(self, version = MaterialVersion.V1_5, expect_issues: int = 0) -> SDict:
        parser = MaterialParser(version)
        parser.convert_bmat(self.bmat)
        self.assertEqual(len(parser.issues), expect_issues, parser.issues)
        self.issues = parser.issues
        builder = MaterialBuilder()
        builder.build_from_bmat(self.bmat)
        self.assertEqual(builder.issues, [])
        return builder.material.value_dict


    def idnames(self):
        return collections.Counter(node.bl_idname for node in self.tree.nodes)


    def test_principled_values(self):
        bsdf = self.shader("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = (0.5, 0.25, 0.1, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.25
        bsdf.inputs["Roughness"].default_value = 0.75

        mat = self.convert()
        self.assertEqual(mat["version"], 1.5)
        self.assertEqual(cast(list[SDict], mat["Stages"])[0], {
            "baseColorFactor": [0.735357, 0.537099, 0.34919, 1.0],
            "metallicFactor": 0.25, "roughnessFactor": 0.75,
        })
        self.assertEqual(self.idnames()[BeamBSDF15.bl_idname], 1)
        self.assertEqual(self.idnames()["ShaderNodeBsdfPrincipled"], 0)


    def test_principled_textures(self):
        bsdf = self.shader("ShaderNodeBsdfPrincipled")
        links = self.tree.links

        albedo = self.image("albedo.png")
        links.new(albedo.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(albedo.outputs["Alpha"], bsdf.inputs["Alpha"])  # base color alpha, no opacity map

        orm = self.image("orm.png")
        separate = self.tree.nodes.new("ShaderNodeSeparateColor")
        links.new(orm.outputs["Color"], separate.inputs[0])
        links.new(separate.outputs["Green"], bsdf.inputs["Roughness"])

        normal_map = self.tree.nodes.new("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = 0.5
        links.new(self.image("normal.png").outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

        stage = cast(list[SDict], self.convert(expect_issues=1)["Stages"])[0]  # packed roughness channel
        self.assertIn("Green", self.issues[0])
        self.assertEqual(stage["baseColorMap"], "albedo.png")
        self.assertNotIn("baseColorFactor", stage)  # linked, factor stays white
        self.assertNotIn("opacityMap", stage)
        self.assertEqual(stage["roughnessMap"], "orm.png")
        self.assertEqual(stage["normalMap"], "normal.png")
        self.assertEqual(stage["normalMapStrength"], 0.5)


    def test_principled_emission(self):
        bsdf = self.shader("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Emission Color"].default_value = (1.0, 0.0, 0.0, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 2.0
        self.assertEqual(cast(list[SDict], self.convert()["Stages"])[0]["emissiveFactor"], [1.0, 0.0, 0.0])


    def test_principled_no_emission_without_strength(self):
        self.shader("ShaderNodeBsdfPrincipled")  # emission color defaults to white, strength 0
        self.assertNotIn("emissiveFactor", cast(list[SDict], self.convert()["Stages"])[0])


    def test_diffuse_to_10(self):
        bsdf = self.shader("ShaderNodeBsdfDiffuse")
        bsdf.inputs["Color"].default_value = (1.0, 0.0, 0.0, 1.0)
        self.tree.links.new(self.image("albedo.png").outputs["Color"], bsdf.inputs["Normal"])

        mat = self.convert(MaterialVersion.V1)
        stage = cast(list[SDict], mat["Stages"])[0]
        self.assertEqual(mat["version"], 1.0)
        self.assertEqual(stage["baseColorFactor"], [1.0, 0.0, 0.0, 1.0])
        self.assertEqual(stage["normalMap"], "albedo.png")
        self.assertEqual(self.idnames()[BeamBDSF10Basic.bl_idname], 1)
        self.assertEqual(self.idnames()[BeamRGBA.bl_idname], 1)


    def test_unsupported_surface(self):
        self.shader("ShaderNodeEmission")
        mat = self.convert(expect_issues=1)
        self.assertEqual(mat["version"], 1.5)
        self.assertEqual(self.idnames()[BeamMaterial.bl_idname], 1)


    def test_force_converts_to_target_version(self):
        self.shader("ShaderNodeBsdfPrincipled").inputs["Base Color"].default_value = (1.0, 0.0, 0.0, 1.0)
        self.convert(MaterialVersion.V1_5)
        mat = self.convert(MaterialVersion.V1)
        self.assertEqual(mat["version"], 1.0)
        self.assertEqual(cast(list[SDict], mat["Stages"])[0]["baseColorFactor"], [1.0, 0.0, 0.0, 1.0])


    def test_beamng_tree_is_kept_without_force(self):
        self.shader("ShaderNodeBsdfPrincipled")
        self.convert()
        nodes = set(node.name for node in self.tree.nodes)
        MaterialParser(MaterialVersion.V1).convert_bmat(self.bmat, force_conversion=False)
        self.assertEqual(set(node.name for node in self.tree.nodes), nodes)
