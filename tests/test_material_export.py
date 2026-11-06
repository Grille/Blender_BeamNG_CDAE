import unittest

import bpy

from grille_cdae.common import *
from grille_cdae.enums import AlphaBlendMode
from grille_cdae.beamng.material import MaterialBuilder, MaterialExportError
from grille_cdae.beamng.material.material import AnimationFlags
from grille_cdae.blender.shader_nodes import (
    BeamMaterial, BeamBSDF15, BeamBDSF10Basic, BeamBSDFCollision, BeamStageMix, BeamUVData, BeamUVAnimation, BeamImageTex, BeamImageTexConverter,
    BeamBSDF15Detail, BeamPalette, ReflectionMode
)

import grille_cdae.addon as addon

S = BeamBSDF15.Sockets
M = BeamMaterial.Sockets
D = BeamBSDF15Detail.Sockets
A = BeamUVAnimation.Sockets


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
            "Stages": [
                {}, {}, {}, {},
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
        self.link(node.outputs[BeamImageTex.Sockets.COLOR_RGB], self.stage.inputs[S.BASE_COLOR_MAP])
        self.assertEqual(self.stage0()["baseColorMap"], "bng.png")


    def test_image_converter(self):
        CS = BeamImageTexConverter.Sockets
        normal = self.node(BeamImageTexConverter.bl_idname)
        normal.inputs[CS.STRENGTH].default_value = 0.5 # pyright: ignore
        self.image_node("normal.png", normal.inputs[CS.COLOR])
        self.link(normal.outputs[CS.NORMAL], self.stage.inputs[S.NORMAL])

        data = self.node(BeamImageTexConverter.bl_idname)
        self.image_node("rough.png", data.inputs[CS.COLOR])
        self.link(data.outputs[CS.DATA], self.stage.inputs[S.ROUGHNESS_MAP])

        stage = self.stage0()
        self.assertEqual(stage["normalMap"], "normal.png")
        self.assertEqual(stage["normalMapStrength"], 0.5)
        self.assertEqual(stage["roughnessMap"], "rough.png")


    def test_image_converter_alpha_from_other_image(self):
        CS = BeamImageTexConverter.Sockets
        self.tree.nodes.remove(self.stage)
        self.stage = self.node(BeamBDSF10Basic.bl_idname)
        self.link(self.stage.outputs[0], self.mat_node.inputs["BNGS"])

        converter = self.node(BeamImageTexConverter.bl_idname)
        self.image_node("color.png", converter.inputs[CS.COLOR])
        alpha = cast(bpy.types.ShaderNodeTexImage, self.node("ShaderNodeTexImage"))
        alpha.image = bpy.data.images.new("alpha.png", 4, 4)
        self.link(alpha.outputs["Alpha"], converter.inputs[CS.ALPHA])
        self.link(converter.outputs[CS.COLOR_RGBA], self.stage.inputs[BeamBDSF10Basic.Sockets.COLOR_MAP])

        self.assertEqual(self.stage0(expect_issues=1)["baseColorMap"], "color.png")
        self.assertIn("alpha.png", self.issues[0].message)


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


    def detail_node(self):
        detail = self.node(BeamBSDF15Detail.bl_idname)
        self.link(detail.outputs["Detail"], self.stage.inputs[S.DETAIL])
        return detail


    def test_detail(self):
        detail = self.detail_node()
        detail.inputs[D.BASE_COLOR_STRENGTH].default_value = 0.5
        uv_data = self.node(BeamUVData.bl_idname)
        uv_data.inputs[BeamUVData.Sockets.DETAIL_SCALE].default_value = (4.0, 8.0)
        color = self.image_node("detail.png", detail.inputs[D.BASE_COLOR_MAP])
        self.link(uv_data.outputs[BeamUVData.Sockets.DETAIL_UV1], color.inputs["Vector"])
        rough = self.image_node("detail_r.png", detail.inputs[D.ROUGHNESS_MAP])
        self.link(uv_data.outputs[BeamUVData.Sockets.DETAIL_UV1], rough.inputs["Vector"])

        stage = self.stage0(expect_issues=1)  # roughness detail map has no uv key in BeamNG
        self.assertEqual(stage["detailMap"], "detail.png")
        self.assertEqual(stage["detailMapUseUV"], 1)
        self.assertEqual(stage["detailBaseColorMapStrength"], 0.5)
        self.assertEqual(stage["roughnessDetailMap"], "detail_r.png")
        self.assertEqual(stage["detailScale"], [4.0, 8.0])
        self.assertIn("uv", self.issues[0].message)


    def test_detail_without_detail_uv_has_scale_one(self):
        detail = self.detail_node()
        self.image_node("detail.png", detail.inputs[D.BASE_COLOR_MAP])
        self.assertEqual(self.stage0()["detailScale"], [1.0, 1.0])


    def test_detail_scale_conflict(self):
        detail = self.detail_node()
        uv_data = self.node(BeamUVData.bl_idname)
        uv_data.inputs[BeamUVData.Sockets.DETAIL_SCALE].default_value = (4.0, 4.0)
        color = self.image_node("detail.png", detail.inputs[D.BASE_COLOR_MAP])
        self.link(uv_data.outputs[BeamUVData.Sockets.DETAIL_UV0], color.inputs["Vector"])
        self.image_node("detail_o.png", detail.inputs[D.OPACITY_MAP])  # plain UV, scale 1
        stage = self.stage0(expect_issues=1)
        self.assertEqual(stage["detailScale"], [4.0, 4.0])
        self.assertIn("detail scales", self.issues[0].message)


    def test_detail_uv_on_main_map_is_reported(self):
        uv_data = self.node(BeamUVData.bl_idname)
        color = self.image_node("albedo.png", self.stage.inputs[S.BASE_COLOR_MAP])
        self.link(uv_data.outputs[BeamUVData.Sockets.DETAIL_UV0], color.inputs["Vector"])
        self.assertNotIn("detailScale", self.stage0(expect_issues=1))


    def test_wrong_node_on_bundle_socket(self):
        palette = self.node(BeamPalette.bl_idname)
        self.link(palette.outputs[BeamPalette.Sockets.PALETTE], self.stage.inputs[S.DETAIL])
        self.stage0(expect_issues=1)
        self.assertIn(BeamBSDF15Detail.bl_label, self.issues[0].message)


    def test_palette(self):
        palette = self.node(BeamPalette.bl_idname)
        self.link(palette.outputs[BeamPalette.Sockets.PALETTE], self.stage.inputs[S.PALETTE])
        self.image_node("palette.png", palette.inputs[BeamPalette.Sockets.PALETTE_MAP])
        palette.inputs[BeamPalette.Sockets.METALLIC].default_value = False
        stage = self.stage0()
        self.assertEqual(stage["colorPaletteMap"], "palette.png")
        self.assertEqual(stage["paletteMetallic"], False)
        self.assertNotIn("paletteBaseColor", stage)  # default True


    def animated_map(self, socket: str):
        uv_data = self.node(BeamUVData.bl_idname)
        anim = self.node(BeamUVAnimation.bl_idname)
        self.link(anim.outputs[A.ANIMATION], uv_data.inputs[BeamUVData.Sockets.ANIMATION])
        tex = self.image_node(f"{socket}.png", self.stage.inputs[socket])
        self.link(uv_data.outputs[BeamUVData.Sockets.UV0], tex.inputs["Vector"])
        return anim


    def test_uv_animation(self):
        anim = self.animated_map(S.BASE_COLOR_MAP)
        anim.inputs[A.MOTION].default_value = BeamUVAnimation.Motion.ROTATE
        anim.inputs[A.ROTATION_SPEED].default_value = 0.5
        anim.inputs[A.ROTATION_PIVOT_OFFSET].default_value = (0.5, 0.25)
        stage = self.stage0()
        self.assertEqual(stage["animFlags"], int(AnimationFlags.ROTATION))
        self.assertEqual(stage["rotSpeed"], 0.5)
        self.assertEqual(stage["rotPivotOffset"], [0.5, 0.25])


    def test_uv_animation_modifiers(self):
        anim = self.animated_map(S.BASE_COLOR_MAP)
        anim.inputs[A.MOTION].default_value = BeamUVAnimation.Motion.SCROLL
        anim.inputs[A.SEQUENCE].default_value = True
        anim.inputs[A.SCROLL_SPEED].default_value = 2.0  # replaced by the wave
        anim.inputs[A.SCROLL_FACTOR].default_value = (1.0, 0.0)
        anim.inputs[A.WAVE_TYPE].default_value = BeamUVAnimation.WaveType.SQUARE
        anim.inputs[A.WAVE_AMPLITUDE].default_value = 0.1
        anim.inputs[A.WAVE_FREQUENCY].default_value = 3.0
        anim.inputs[A.FRAMES_SEC].default_value = 10.0
        anim.inputs[A.FRAMES].default_value = 4.0

        stage = self.stage0()
        self.assertEqual(stage["animFlags"], int(AnimationFlags.SCROLL | AnimationFlags.WAVE | AnimationFlags.SEQUENCE))
        self.assertNotIn("scrollSpeed", stage)
        self.assertEqual(stage["scrollDir"], [1.0, 0.0])
        self.assertEqual(stage["waveType"], "Square")
        self.assertEqual(stage["waveAmp"], 0.1)
        self.assertEqual(stage["waveFreq"], 3.0)
        self.assertEqual(stage["sequenceFramePerSec"], 10.0)
        self.assertEqual(stage["sequenceSegmentSize"], 0.25)


    def test_uv_animation_rotate_wave_scale(self):
        anim = self.animated_map(S.BASE_COLOR_MAP)
        anim.inputs[A.MOTION].default_value = BeamUVAnimation.Motion.ROTATE
        anim.inputs[A.WAVE_TYPE].default_value = BeamUVAnimation.WaveType.SIN
        anim.inputs[A.SCALE].default_value = True
        anim.inputs[A.ROTATION_SPEED].default_value = 0.5  # replaced by the wave
        anim.inputs[A.ROTATION_PIVOT_OFFSET].default_value = (0.5, 0.25)  # reset by the wave scale
        stage = self.stage0()
        self.assertEqual(stage["animFlags"], int(AnimationFlags.ROTATION | AnimationFlags.WAVE | AnimationFlags.SCALE))
        for key in ("rotSpeed", "rotPivotOffset"): self.assertNotIn(key, stage)


    def test_uv_animation_scroll_lost_to_wave_scale(self):
        anim = self.animated_map(S.BASE_COLOR_MAP)
        anim.inputs[A.MOTION].default_value = BeamUVAnimation.Motion.SCROLL
        anim.inputs[A.WAVE_TYPE].default_value = BeamUVAnimation.WaveType.SIN
        anim.inputs[A.SCALE].default_value = True
        anim.inputs[A.SCROLL_FACTOR].default_value = (1.0, 0.0)
        stage = self.stage0(expect_issues=1)
        self.assertEqual(stage["animFlags"], int(AnimationFlags.WAVE | AnimationFlags.SCALE))
        self.assertNotIn("scrollDir", stage)
        self.assertIn(A.SCALE.value, self.issues[0].message)


    def test_uv_animation_modifiers_without_effect(self):
        anim = self.animated_map(S.BASE_COLOR_MAP)
        anim.inputs[A.WAVE_TYPE].default_value = BeamUVAnimation.WaveType.SIN  # no motion, no scale
        anim.inputs[A.WAVE_AMPLITUDE].default_value = 0.1
        anim.inputs[A.SEQUENCE].default_value = True
        anim.inputs[A.FRAMES].default_value = 4.0
        self.assertEqual(self.stage0()["animFlags"], int(AnimationFlags.SEQUENCE))

        anim.inputs[A.SEQUENCE].default_value = False
        anim.inputs[A.WAVE_TYPE].default_value = BeamUVAnimation.WaveType.NONE
        anim.inputs[A.SCALE].default_value = True  # no wave, no sequence
        self.assertNotIn("animFlags", self.stage0())


    def test_uv_animation_wave_scale(self):
        anim = self.animated_map(S.BASE_COLOR_MAP)
        anim.inputs[A.SCALE].default_value = True
        anim.inputs[A.WAVE_TYPE].default_value = BeamUVAnimation.WaveType.SIN
        stage = self.stage0()
        self.assertEqual(stage["animFlags"], int(AnimationFlags.WAVE | AnimationFlags.SCALE))
        self.assertNotIn("waveType", stage)  # Sin is the default


    def test_uv_animation_disabled_parts_not_written(self):
        anim = self.animated_map(S.BASE_COLOR_MAP)
        anim.inputs[A.MOTION].default_value = BeamUVAnimation.Motion.SCROLL
        anim.inputs[A.SCROLL_SPEED].default_value = 2.0
        anim.inputs[A.ROTATION_SPEED].default_value = 0.5  # rotate off
        anim.inputs[A.WAVE_AMPLITUDE].default_value = 0.1  # wave type None
        anim.inputs[A.FRAMES_SEC].default_value = 10.0  # sequence off
        stage = self.stage0()
        self.assertEqual(stage["animFlags"], int(AnimationFlags.SCROLL))
        self.assertEqual(stage["scrollSpeed"], 2.0)
        for key in ("rotSpeed", "waveAmp", "sequenceFramePerSec", "sequenceSegmentSize"): self.assertNotIn(key, stage)


    def test_uv_animation_sequence_without_frames(self):
        anim = self.animated_map(S.BASE_COLOR_MAP)
        anim.inputs[A.SEQUENCE].default_value = True
        anim.inputs[A.FRAMES_SEC].default_value = 10.0
        stage = self.stage0(expect_issues=1)
        self.assertNotIn("sequenceSegmentSize", stage)
        self.assertIn(A.FRAMES.value, self.issues[0].message)


    def test_uv_animation_conflict(self):
        for socket, speed in ((S.BASE_COLOR_MAP, 1.0), (S.ROUGHNESS_MAP, 2.0)):
            anim = self.animated_map(socket)
            anim.inputs[A.MOTION].default_value = BeamUVAnimation.Motion.ROTATE
            anim.inputs[A.ROTATION_SPEED].default_value = speed
        self.assertEqual(self.stage0(expect_issues=1)["rotSpeed"], 1.0)
        self.assertIn("UV animations", self.issues[0].message)


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
            "translucent": True, "translucentZWrite": True,  # LerpAlpha is the file default
            "cubemap": "global_cubemap",
        })


    def test_level_reflection(self):
        self.mat_node.reflection_mode = ReflectionMode.LEVEL
        mat = self.build()
        self.assertEqual(mat["dynamicCubemap"], True)
        self.assertNotIn("cubemap", mat)


    def test_invert_backface_normals_needs_double_sided(self):
        self.assertNotIn("invertBackFaceNormals", self.build())


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


    def mix(self, base: bpy.types.Node | None, overlay: bpy.types.Node | None):
        mix = self.node(BeamStageMix.bl_idname)
        if base: self.link(base.outputs[0], mix.inputs[BeamStageMix.Sockets.BASE])
        if overlay: self.link(overlay.outputs[0], mix.inputs[BeamStageMix.Sockets.OVERLAY])
        return mix


    def new_stage(self, roughness: float):
        stage = self.node(BeamBSDF15.bl_idname)
        stage.inputs[S.ROUGHNESS_FACTOR].default_value = roughness
        return stage


    def test_stage_mix(self):
        # ((0.1, 0.2), 0.3) -> stages in order base to overlay
        mix = self.mix(self.mix(self.new_stage(0.1), self.new_stage(0.2)), self.new_stage(0.3))
        self.link(mix.outputs[0], self.mat_node.inputs["BNGS"])
        mat = self.build()
        stages = cast(list[SDict], mat["Stages"])
        self.assertEqual(mat["activeLayers"], 3)
        self.assertEqual([s.get("roughnessFactor") for s in stages], [0.1, 0.2, 0.3, None])


    def test_stage_mix_missing_input(self):
        mix = self.mix(self.new_stage(0.1), None)
        self.link(mix.outputs[0], self.mat_node.inputs["BNGS"])
        self.assertNotIn("activeLayers", self.build(expect_issues=1))


    def test_mixed_versions(self):
        mix = self.mix(self.new_stage(0.1), self.node(BeamBDSF10Basic.bl_idname))
        self.link(mix.outputs[0], self.mat_node.inputs["BNGS"])
        with self.assertRaisesRegex(MaterialExportError, "can't be mixed"):
            self.build()


    def test_too_many_stages(self):
        a = self.mix(self.new_stage(0.1), self.new_stage(0.2))
        b = self.mix(self.new_stage(0.3), self.mix(self.new_stage(0.4), self.new_stage(0.5)))
        self.link(self.mix(a, b).outputs[0], self.mat_node.inputs["BNGS"])
        with self.assertRaisesRegex(MaterialExportError, "5 stages"):
            self.build()
