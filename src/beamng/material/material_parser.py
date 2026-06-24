import bpy

from ...blender.enums import *
from ...blender.shader_nodes import *
from ...blender.shader_node_builder import NodeTreeBuilder
from .material import Material, MaterialVersion
from ..numerics import *


class MaterialParser:
   
    def __init__(self, version: MaterialVersion):
        self.version = version
    

    def parse_to_bmat(self, src: Material, dst: bpy.types.Material):

        tree = NodeTreeBuilder(dst.node_tree)
        tree.clear()

        out = tree.create_node(NodeName.OutputMaterial)
        mat = tree.create_node(BeamMaterial.bl_idname)
        tree.link(mat, SocketName.Shader, out, SocketName.Surface)

        if self.version == MaterialVersion.V1:
            bdsf = self._parse_to_tree_10(src, tree)
        elif self.version == MaterialVersion.V1_5:
            bdsf = self._parse_to_tree_15(src, tree)
        else:
            raise Exception()
        
        tree.link(bdsf, SocketName.BSDF, mat, SocketName.Shader)

        tree.arrange_nodes(300, 150)


    def _parse_to_tree_10(self, src: Material, tree: NodeTreeBuilder):

        src0 = src.stages[0]
        
        color = Color4F.from_list4(src0.color.factor).linear.tuple4
        bdsf = tree.create_node(BeamBDSF10Basic.bl_idname, [color] )

        if src0.color.map is not None:
            timg = tree.create_teximage(src0.color.map, ColorSpace.SRGB)
            tree.link(timg, SocketName.Color, bdsf, SocketName.BaseColor)

        return bdsf
    

    def _parse_to_tree_15(self, src: Material,  tree: NodeTreeBuilder):

        src0 = src.stages[0]

        color = Color4F.from_list4(src0.color.factor).linear.tuple4
        bdsf = tree.create_node(BeamBSDF15.bl_idname, [color] )

        if src0.color.map is not None:
            timg = tree.create_teximage(src0.color.map, ColorSpace.NON_COLOR)
            tree.link(timg, SocketName.Color, bdsf, SocketName.BaseColor)

        return bdsf


   