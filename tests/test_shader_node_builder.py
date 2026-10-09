import unittest

import bpy

from grille_cdae.common import *
from grille_cdae.enums import *
from grille_cdae.blender.shader_node_builder import NodeTreeBuilder, NodeSignature



INNER = NodeSignature(
    ("Color", SocketType.Color),
    ("Enabled", SocketType.Bool),
)
OUTER = NodeSignature(
    ("Value", SocketType.Float),
    ("Inner", INNER),
)



class ShaderNodeBuilderTest(unittest.TestCase):

    def setUp(self):
        self.tree = cast(bpy.types.ShaderNodeTree, bpy.data.node_groups.new("builder_test", "ShaderNodeTree"))
        self.ntb = NodeTreeBuilder(self.tree)


    def tearDown(self):
        bpy.data.node_groups.remove(self.tree)


    def value(self):
        return self.ntb.nc.node(bpy.types.ShaderNodeValue)


    def test_true_division(self):
        value = self.value()
        for result, linked, constant in ((value / 2, 0, 1), (2 / value, 1, 0)):
            node = cast(bpy.types.ShaderNodeMath, cast(Any, result).node)
            self.assertEqual(node.operation, "DIVIDE")
            self.assertTrue(node.inputs[linked].is_linked)
            self.assertEqual(node.inputs[constant].default_value, 2)


    def test_mix_bundle(self):
        nc = self.ntb.nc
        a = nc.combine_bundle(OUTER)
        b = nc.combine_bundle(OUTER)
        result = nc.mix_bundle(OUTER, 0.5, a[0], b[0])

        combine = cast(Any, result).node
        self.assertEqual(combine.bl_idname, "NodeCombineBundle")
        self.assertEqual(result.get_output(), combine.outputs[0])
        for name in ("Value", "Inner"): self.assertTrue(combine.inputs[name].is_linked, name)

        inner = combine.inputs["Inner"].links[0].from_node
        self.assertEqual(inner.bl_idname, "NodeCombineBundle")
        for name in ("Color", "Enabled"): self.assertTrue(inner.inputs[name].is_linked, name)
