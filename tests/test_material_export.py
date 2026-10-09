import unittest

import bpy

from grille_cdae.common import *
from grille_cdae.enums import AlphaBlendMode
from grille_cdae.beamng.material import MaterialBuilder, MaterialExportError
from grille_cdae.blender.shader_nodes import (
    BeamMaterial, BeamBSDF15, BeamBSDFCollision, BeamStageMix, BeamUVData, BeamImageTex, BeamBSDF15Detail, ReflectionMode
)

import grille_cdae.addon as addon

S = BeamBSDF15.Sockets
M = BeamMaterial.Sockets


def setUpModule(): addon.register()
def tearDownModule(): addon.unregister()



class MaterialExportTest(unittest.TestCase):

    def setUp(self):
        self.bmat = bpy.data.materials.new("test_mat")
        self.tree = not_none(self.bmat.node_tree)
        self.tree.nodes.clear()
        self.output = self.node("ShaderNodeOutputMaterial")
        self.mat_node = cast(BeamMaterial, self.node(BeamMaterial.bl_idname))
        self.stage = self.node(BeamBSDF15.bl_idname)
        self.link(self.mat_node.outputs["Shader"], self.output.inputs["Surface"])
        self.link(self.stage.outputs["BNGS"], self.mat_node.inputs["BNGS"])


    def tearDown(self):
        bpy.data.materials.remove(self.bmat)
        for image in list(bpy.data.images): bpy.data.images.remove(image)


    def node(self, idname: str) -> bpy.types.Node:
        return self.tree.nodes.new(idname)


    def link(self, a: bpy.types.NodeSocket, b: bpy.types.NodeSocket):
        return self.tree.links.new(a, b)


    def image_node(self, name: str, target: bpy.types.NodeSocket):
        node = cast(bpy.types.ShaderNodeTexImage, self.node("ShaderNodeTexImage"))
        node.image = bpy.data.images.new(name, 4, 4)
        self.link(node.outputs["Color"], target)
        return node


    def build(self, expect_issues: int = 0):
        builder = MaterialBuilder()
        builder.build_from_bmat(self.bmat)
        self.assertEqual(len(builder.issues), expect_issues, [str(i) for i in builder.issues])
        self.issues = builder.issues
        return builder.material.value_dict


    def stage0(self, expect_issues: int = 0) -> SDict:
        return cast(list[SDict], self.build(expect_issues)["Stages"])[0]


    def test_default_tree(self):
        self.assertEqual(self.build(), {
            "name": "test_mat",
            "mapTo": "test_mat",
            "class": "Material",
            "version": 1.5,
            "dynamicCubemap": False,
            "Stages": [
                {"metallicFactor": 1.0, "roughnessFactor": 1.0, "opacityFactor": 1.0, "clearCoatFactor": 0.0},
                {}, {}, {},
            ],
        })


    def test_values(self):
        self.stage.inputs[S.BASE_COLOR].default_value = (0.5, 0.25, 0.1, 1.0)
        self.stage.inputs[S.ROUGHNESS_FACTOR].default_value = 0.3
        self.stage.inputs[S.VERTEX_COLOR].default_value = True
        self.stage.inputs[S.EMISSIVE_FACTOR].default_value = (1.0, 0.0, 0.0, 1.0)
        stage = self.stage0()
        self.assertEqual(stage["baseColorFactor"], [0.735357, 0.537099, 0.34919, 1.0])  # linear -> sRGB
        self.assertEqual(stage["roughnessFactor"], 0.3)
        self.assertEqual(stage["vertColor"], True)
        self.assertEqual(stage["emissiveFactor"], [1.0, 0.0, 0.0])  # 3 components, like BeamNG's 1.5 files


    def test_maps_and_uv(self):
        color = self.image_node("albedo.png", self.stage.inputs[S.BASE_COLOR_MAP])
        uv_data = self.node(BeamUVData.bl_idname)
        self.link(uv_data.outputs[BeamUVData.Sockets.UV1], color.inputs["Vector"])

        rough = self.image_node("rough.png", self.stage.inputs[S.ROUGHNESS_MAP])
        uv_map = cast(bpy.types.ShaderNodeUVMap, self.node("ShaderNodeUVMap"))
        uv_map.uv_map = "UVMap1"
        self.link(uv_map.outputs["UV"], rough.inputs["Vector"])

        self.image_node("ao.png", self.stage.inputs[S.AO_MAP])

        stage = self.stage0()
        self.assertEqual(stage["baseColorMap"], "albedo.png")
        self.assertEqual(stage["diffuseMapUseUV"], 1)
        self.assertEqual(stage["roughnessMap"], "rough.png")
        self.assertEqual(stage["roughnessMapUseUV"], 1)
        self.assertEqual(stage["ambientOcclusionMap"], "ao.png")
        self.assertNotIn("ambientOcclusionMapUseUV", stage)


    def test_normal_map_strength(self):
        normal_map = self.node("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = 0.5
        self.image_node("normal.png", normal_map.inputs["Color"])
        self.link(normal_map.outputs["Normal"], self.stage.inputs[S.NORMAL])

        stage = self.stage0()
        self.assertEqual(stage["normalMap"], "normal.png")
        self.assertEqual(stage["normalMapStrength"], 0.5)


    def test_beam_image_tex(self):
        node = cast(BeamImageTex, self.node(BeamImageTex.bl_idname))
        node.image = bpy.data.images.new("bng.png", 4, 4)
        self.link(node.outputs[BeamImageTex.ImageType.COLOR_RGB], self.stage.inputs[S.BASE_COLOR_MAP])
        self.assertEqual(self.stage0()["baseColorMap"], "bng.png")


    def test_reroute_and_muted_link(self):
        reroute = self.node("NodeReroute")
        self.image_node("albedo.png", reroute.inputs[0])
        self.link(reroute.outputs[0], self.stage.inputs[S.BASE_COLOR_MAP])

        muted = self.image_node("muted.png", self.stage.inputs[S.METALLIC_MAP])
        muted.outputs["Color"].links[0].is_muted = True

        stage = self.stage0()
        self.assertEqual(stage["baseColorMap"], "albedo.png")
        self.assertNotIn("metallicMap", stage)


    def test_constant_value_node(self):
        value = self.node("ShaderNodeValue")
        value.outputs[0].default_value = 0.25
        self.link(value.outputs[0], self.stage.inputs[S.METALLIC_FACTOR])
        self.assertEqual(self.stage0()["metallicFactor"], 0.25)


    def test_linked_value_is_reported(self):
        self.stage.inputs[S.METALLIC_FACTOR].default_value = 0.5
        math = self.node("ShaderNodeMath")
        self.link(math.outputs[0], self.stage.inputs[S.METALLIC_FACTOR])
        self.assertEqual(self.stage0(expect_issues=1)["metallicFactor"], 0.5)
        self.assertIn("Metallic Factor", self.issues[0].message)


    def test_map_problems_are_reported(self):
        self.node("ShaderNodeTexImage")  # unrelated
        empty = self.node("ShaderNodeTexImage")
        self.link(empty.outputs["Color"], self.stage.inputs[S.BASE_COLOR_MAP])
        rgb = self.node("ShaderNodeRGB")
        self.link(rgb.outputs[0], self.stage.inputs[S.ROUGHNESS_MAP])
        stage = self.stage0(expect_issues=2)
        self.assertNotIn("baseColorMap", stage)
        self.assertNotIn("roughnessMap", stage)


    def test_unsupported_sockets_are_reported(self):
        detail = self.node(BeamBSDF15Detail.bl_idname)
        self.link(detail.outputs["Detail"], self.stage.inputs[S.DETAIL])
        self.stage0(expect_issues=1)
        self.assertIn("Detail", self.issues[0].message)


    def test_material_settings(self):
        self.mat_node.inputs[M.CLIP].default_value = True
        self.mat_node.inputs[M.CLIP_T].default_value = 0.5
        self.mat_node.inputs[M.DOUBLE_SIDED].default_value = True
        self.mat_node.inputs[M.SHADOWS].default_value = False
        self.mat_node.inputs[M.SUBSURFACE_SCATTERING].default_value = 0.3
        self.mat_node.blend_mode = AlphaBlendMode.LERP_ALPHA
        self.mat_node.blend_z = True
        self.mat_node.reflection_mode = ReflectionMode.CUBEMAP
        self.mat_node.reflection_cubemap = "global_cubemap"

        mat = self.build()
        mat.pop("Stages")
        self.assertEqual(mat, {
            "name": "test_mat", "mapTo": "test_mat", "class": "Material", "version": 1.5,
            "alphaTest": True, "alphaRef": 128,
            "doubleSided": True, "invertBackFaceNormals": True,
            "castShadows": False,
            "subSurface": True, "subSurfaceIntensity": 0.3,
            "translucent": True, "translucentBlendOp": "LerpAlpha", "translucentZWrite": True,
            "dynamicCubemap": False, "cubemap": "global_cubemap",
        })


    def test_invert_backface_normals_needs_double_sided(self):
        self.assertNotIn("invertBackFaceNormals", self.build())


    @unittest.skip("BeamBSDFCollision has no output socket yet")
    def test_collision(self):
        self.tree.nodes.remove(self.mat_node)
        collision = self.node(BeamBSDFCollision.bl_idname)
        self.link(collision.outputs[0], self.output.inputs["Surface"])
        mat = self.build()
        self.assertEqual(mat["version"], 1.0)
        self.assertEqual(mat["castShadows"], False)


    def test_not_a_beamng_tree(self):
        self.tree.nodes.remove(self.mat_node)
        principled = self.node("ShaderNodeBsdfPrincipled")
        self.link(principled.outputs[0], self.output.inputs["Surface"])
        with self.assertRaisesRegex(MaterialExportError, "BNG Material"):
            self.build()


    def test_stage_mix_not_supported_yet(self):
        mix = self.node(BeamStageMix.bl_idname)
        self.link(mix.outputs[0], self.mat_node.inputs["BNGS"])
        with self.assertRaisesRegex(MaterialExportError, "not supported"):
            self.build()
