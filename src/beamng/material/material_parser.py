import bpy

from ...blender.enums import *
from ...blender.shader_nodes import *
from ...blender.shader_node_builder import NodeTreeBuilder
from .material import Material, MaterialVersion
from . material_builder import MaterialBuilder
from ..numerics import *


class MaterialParser:
   
    def __init__(self, target_version: MaterialVersion):
        self.target_version = target_version
        self.force_alpha_clip = False


    def convert_bmat(self, bmat: bpy.types.Material, force_conversion: bool = True):

        builder = MaterialBuilder(MaterialVersion.NONE)
        mat = builder.build_from_bmat(bmat)

        if (mat.version == MaterialVersion.NONE or force_conversion):
            self.parse_to_bmat(mat, bmat)
    

    def parse_to_bmat(self, src: Material, dst: bpy.types.Material):

        tree = NodeTreeBuilder(dst.node_tree)
        tree.clear()

        out = tree.create_node(NodeName.OutputMaterial)
        mat = tree.create_node(BeamMaterial.bl_idname)
        tree.link(mat, SocketName.Shader, out, SocketName.Surface)

        if self.force_alpha_clip:
            mat.inputs[BeamMaterial.Sockets.CLIP].default_value = True
            mat.inputs[BeamMaterial.Sockets.CLIP_T].default_value = 0.5

        if self.target_version == MaterialVersion.V1:
            bdsf = self._parse_to_tree_10(src, tree)
        elif self.target_version == MaterialVersion.V1_5:
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
            tree.link(timg, SocketName.Alpha, bdsf, SocketName.BaseAlpha)

        return bdsf
    

    def _parse_to_tree_15(self, src: Material,  tree: NodeTreeBuilder):

        src0 = src.stages[0]

        color = Color4F.from_list4(src0.color.factor).linear.tuple4
        bdsf = tree.create_node(BeamBSDF15.bl_idname, [color] )

        if src0.color.map is not None:
            timg = tree.create_teximage(src0.color.map, ColorSpace.NON_COLOR)
            tree.link(timg, SocketName.Color, bdsf, SocketName.BaseColor)

        return bdsf


   