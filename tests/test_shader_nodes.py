import unittest

import bpy

from grille_cdae.common import *
from grille_cdae.enums import *
from grille_cdae.blender.shader_nodes import ShaderNodeRegistry, BaseShaderNode, BeamRGBAMath, BeamImageTex, BeamBSDF15, BeamBSDFCollision, BeamUVAnimation, BeamUVData, ImageType, BeamBDSF10Basic, BeamImageTexConverter
from grille_cdae.blender.shader_nodes import NODE_GROUP_VERSION_MAYOR_KEY, NODE_GROUP_VERSION_MINOR_KEY, update_node_groups, apply_deferred_updates

import grille_cdae.addon as addon


def setUpModule(): addon.register()
def tearDownModule(): addon.unregister()



class ShaderNodesTest(unittest.TestCase):
    """Builds the node group of every custom node (and its variants) from scratch."""

    def setUp(self):
        self.bmat = bpy.data.materials.new("nodes")
        self.tree = not_none(self.bmat.node_tree)


    def tearDown(self):
        bpy.data.materials.remove(self.bmat)
        for group in list(bpy.data.node_groups): bpy.data.node_groups.remove(group)
        for image in list(bpy.data.images): bpy.data.images.remove(image)


    def new(self, cls: type[BaseShaderNode]):
        return cast(BaseShaderNode, self.tree.nodes.new(cls.bl_idname))


    def build(self, node: BaseShaderNode):
        # Blender only prints exceptions raised in init / update callbacks, rebuild directly so they surface
        name = node.get_node_group_name()
        if name in bpy.data.node_groups: bpy.data.node_groups.remove(bpy.data.node_groups[name])
        node.init(bpy.context)

        tree = not_none(node.node_tree)
        self.assertEqual(tree.name, name)
        self.assertFalse(node.is_node_group_outdated)


    def test_build_all_nodes(self):
        for cls in ShaderNodeRegistry.nodes:
            with self.subTest(cls.__name__):
                self.build(self.new(cls))


    def test_shared_group(self):
        for cls in ShaderNodeRegistry.nodes:
            with self.subTest(cls.__name__):
                self.assertEqual(self.new(cls).node_tree, self.new(cls).node_tree)


    def test_menu_defaults(self):
        # menu items come from the linked Menu Switch, a default set before linking would be lost
        for cls in ShaderNodeRegistry.nodes:
            node = self.new(cls)
            for socket in node.inputs:
                if socket.type == "MENU":
                    with self.subTest(f"{cls.__name__}.{socket.name}"):
                        self.assertNotEqual(cast(bpy.types.NodeSocketMenu, socket).default_value, "")


    def test_minor_update_keeps_links_and_values(self):
        node = self.new(BeamBSDFCollision)
        not_none(node.node_tree)[NODE_GROUP_VERSION_MINOR_KEY] = -1
        rgb = self.tree.nodes.new("ShaderNodeRGB")
        self.tree.links.new(rgb.outputs[0], node.inputs["Color"])
        display = node.inputs["Display"]
        cast(bpy.types.NodeSocketBool, display).default_value = False
        display.display_shape = "CIRCLE"
        display.hide = True

        update_node_groups()

        self.assertFalse(node.is_node_group_outdated)
        self.assertEqual(not_none(node.node_tree).name, node.get_node_group_name())
        self.assertEqual([link.from_node for link in node.inputs["Color"].links], [rgb])
        display = node.inputs["Display"]
        self.assertFalse(cast(bpy.types.NodeSocketBool, display).default_value)
        self.assertEqual(display.display_shape, "CIRCLE_DOT")
        self.assertTrue(display.hide)


    def test_minor_update_nested_groups(self):
        # outer and nested groups all stale, removing an outer group removes the nodes nested in it
        node = self.new(BeamBSDF15)
        for group in bpy.data.node_groups: group[NODE_GROUP_VERSION_MINOR_KEY] = -1

        update_node_groups()

        self.assertFalse(node.is_node_group_outdated)
        self.assertFalse([group.name for group in bpy.data.node_groups if group.name.endswith("_outdated")])
        for tree in [self.tree, *bpy.data.node_groups]:
            for inner in tree.nodes:
                if isinstance(inner, BaseShaderNode):
                    with self.subTest(f"{tree.name}/{inner.name}"):
                        self.assertFalse(inner.is_node_group_outdated)


    def fake_old_mayor(self, node: BaseShaderNode, old_names: dict[str, str]):
        """Turns the node's group into one from the previous major version, with sockets renamed back."""
        group = not_none(node.node_tree)
        group.name = f"{group.name}_old"
        group[NODE_GROUP_VERSION_MAYOR_KEY] = node.ng_version_mayor - 1
        for item in not_none(group.interface).items_tree:
            if item.name in old_names: item.name = old_names[item.name]
        group.interface_update(bpy.context)
        self.assertTrue(node.is_node_group_mayor_outdated)


    def update_with_renames(self, node: BaseShaderNode, renames: dict[str, str]) -> list[str]:
        """Runs the major update as if the node declared the renames, nodes stay at version 0 until the rework is released."""
        cls = type(node)
        cls.get_socket_renames = lambda self, saved: renames # pyright: ignore[reportAttributeAccessIssue]
        try: return node.update_node_group_mayor()
        finally: del cls.get_socket_renames # pyright: ignore[reportAttributeAccessIssue]


    def test_mayor_update_follows_renames(self):
        LS = BeamUVAnimation.Sockets
        renames = {"Scroll Speed": str(LS.MOTION_SPEED), "Scroll Factor": str(LS.MOTION_DIRECTION)}
        node = self.new(BeamUVAnimation)
        self.fake_old_mayor(node, {new: old for old, new in renames.items()})
        cast(bpy.types.NodeSocketMenu, node.inputs[LS.MOTION]).default_value = BeamUVAnimation.Motion.SCROLL
        cast(bpy.types.NodeSocketFloat, node.inputs["Scroll Speed"]).default_value = 2.5
        direction = self.tree.nodes.new("ShaderNodeCombineXYZ")
        self.tree.links.new(direction.outputs[0], node.inputs["Scroll Factor"])
        uv_data = self.tree.nodes.new(BeamUVData.bl_idname)
        self.tree.links.new(node.outputs[LS.ANIMATION], uv_data.inputs[BeamUVData.Sockets.ANIMATION])

        self.assertEqual(self.update_with_renames(node, renames), [])

        self.assertFalse(node.is_node_group_outdated)
        self.assertEqual(cast(bpy.types.NodeSocketMenu, node.inputs[LS.MOTION]).default_value, BeamUVAnimation.Motion.SCROLL)
        self.assertAlmostEqual(cast(bpy.types.NodeSocketFloat, node.inputs[LS.MOTION_SPEED]).default_value, 2.5)
        self.assertEqual([link.from_node for link in node.inputs[LS.MOTION_DIRECTION].links], [direction])
        self.assertEqual([link.to_node for link in node.outputs[LS.ANIMATION].links], [uv_data])


    def test_mayor_update_operator(self):
        node = self.new(BeamBSDFCollision)
        self.fake_old_mayor(node, {"Color": "Tint"})
        cast(bpy.types.NodeSocketColor, node.inputs["Tint"]).default_value = (1, 0, 0, 1)

        with bpy.context.temp_override(node=node):
            self.assertEqual(bpy.ops.grille.update_beamng_node(), {'FINISHED'})

        # the identifier survives on the new socket, it must start at the group default, not the old value
        self.assertFalse(node.is_node_group_outdated)
        self.assertEqual(tuple(cast(bpy.types.NodeSocketColor, node.inputs["Color"]).default_value), (1, 0, 1, 1))


    def test_mayor_update_reports_lost(self):
        # removed with a changed value is reported, unchanged isn't
        node = self.new(BeamBSDFCollision)
        self.fake_old_mayor(node, {"Color": "Tint", "Display": "Show"})
        cast(bpy.types.NodeSocketColor, node.inputs["Tint"]).default_value = (1, 0, 0, 1)
        self.assertEqual(node.update_node_group_mayor(), ["Input 'Tint' removed"])
        self.assertTrue(cast(bpy.types.NodeSocketBool, node.inputs["Display"]).default_value)


    def test_mayor_update_renamed_outputs(self):
        # outputs follow renames too, post_init runs after restoring so the type picks the visible ones
        LS = BeamImageTex.Sockets
        renames = {"Old RGBA": str(LS.COLOR_RGBA), "Old RGB": str(LS.COLOR_RGB)}
        node = cast(BeamImageTex, self.new(BeamImageTex))
        node.image_type = ImageType.NORMAL
        self.fake_old_mayor(node, {new: old for old, new in renames.items()})
        bsdf = self.new(BeamBDSF10Basic)
        self.tree.links.new(node.outputs["Old RGBA"], bsdf.inputs[BeamBDSF10Basic.Sockets.COLOR_MAP])

        self.assertEqual(self.update_with_renames(node, renames), [])

        self.assertTrue(node.outputs[LS.COLOR_RGBA].is_linked)
        self.assertEqual([s.name for s in node.outputs if not s.hide], [LS.COLOR_RGBA, LS.NORMAL])


    def test_image_tex_group_found_by_image(self):
        # group names don't identify the image, images get renamed and Blender 4.5 cuts names at 63 bytes
        image = bpy.data.images.new("tex_a", 4, 4)
        first = cast(BeamImageTex, self.new(BeamImageTex))
        first.image = image
        group = not_none(first.node_tree)
        image.name = "tex_renamed"
        group.name = f"{BaseShaderNode.get_node_group_name(first)}_tex_"

        second = cast(BeamImageTex, self.new(BeamImageTex))
        second.image = image
        third = cast(BeamImageTex, self.new(BeamImageTex))
        third.image = bpy.data.images.new("tex_b", 4, 4)

        self.assertEqual(second.node_tree, group)
        self.assertNotEqual(third.node_tree, group)


    def test_image_output_follows_link(self):
        LS = BeamImageTex.Sockets
        for node_type in (BeamImageTex, BeamImageTexConverter):
            with self.subTest(node_type.bl_label):
                node = cast(BeamImageTex, self.new(node_type))
                bsdf = self.tree.nodes.new("ShaderNodeBsdfPrincipled")
                cases = (("Roughness", LS.DATA), ("Normal", LS.NORMAL), ("Base Color", LS.COLOR_RGB))
                for target, expected in cases:
                    dragged = LS.COLOR_RGB if expected != LS.COLOR_RGB else LS.DATA
                    self.tree.links.new(node.outputs[dragged], bsdf.inputs[target])
                    # links only move after the tree update, the editor's link operator is still running inside it
                    self.assertTrue(node.outputs[dragged].is_linked)
                    apply_deferred_updates()
                    self.assertEqual(node.image_type, expected)
                    self.assertTrue(node.outputs[expected].is_linked)
                # every link sits on the output its target expects, unlinked other outputs are hidden
                self.assertEqual([s.name for s in node.outputs if not s.hide], [LS.COLOR_RGB, LS.NORMAL, LS.DATA])
                self.assertEqual(sum(len(not_none(s.links)) for s in node.outputs), 3)
                # unlinked outputs hide again
                for link in list(not_none(node.outputs[LS.NORMAL].links)): self.tree.links.remove(link)
                apply_deferred_updates()
                self.assertTrue(node.outputs[LS.NORMAL].hide)


    def test_image_output_none_keeps_links(self):
        LS = BeamImageTex.Sockets
        node = cast(BeamImageTex, self.new(BeamImageTex))
        node.image_type = ImageType.NONE
        bsdf = self.tree.nodes.new("ShaderNodeBsdfPrincipled")
        self.tree.links.new(node.outputs[LS.COLOR_RGB], bsdf.inputs["Roughness"])
        apply_deferred_updates()
        self.assertTrue(node.outputs[LS.COLOR_RGB].is_linked)
        self.assertEqual(node.image_type, ImageType.NONE)


    def test_rgba_math_operations(self):
        # Internal node, only the operations the node groups use, others are allowed to throw
        node = cast(BeamRGBAMath, self.new(BeamRGBAMath))
        for operation in (Operation.MULTIPLY, Operation.HARD_LIGHT, Operation.OVERLAY):
            with self.subTest(operation):
                node.operation = operation.value
                self.build(node)


    def test_image_tex_with_image(self):
        node = cast(BeamImageTex, self.new(BeamImageTex))
        node.image = bpy.data.images.new("tex.png", 4, 4)
        self.build(node)
        self.assertIn("tex.png", not_none(node.node_tree).name)


    def test_bsdf15_validates_image_colorspace(self):
        node = self.new(BeamBSDF15)
        image_node = cast(bpy.types.ShaderNodeTexImage, self.tree.nodes.new("ShaderNodeTexImage"))
        image_node.image = image = bpy.data.images.new("albedo.png", 4, 4)
        self.tree.links.new(image_node.outputs["Color"], node.inputs[BeamBSDF15.Sockets.BASE_COLOR_MAP])

        not_none(image.colorspace_settings).name = "sRGB"
        node.update()
        self.assertEqual(node.runtime.messages, [f"- {BeamBSDF15.Sockets.BASE_COLOR_MAP.value}:", "Non-Color Expected"])

        not_none(image.colorspace_settings).name = "Non-Color"
        node.update()
        self.assertEqual(node.runtime.messages, [])
