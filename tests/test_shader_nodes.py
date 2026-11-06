import unittest

import bpy

from grille_cdae.common import *
from grille_cdae.enums import *
from grille_cdae.blender.shader_nodes import ShaderNodeRegistry, BaseShaderNode, BeamRGBAMath, BeamImageTex, BeamBSDF15

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
