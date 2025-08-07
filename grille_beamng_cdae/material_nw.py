import bpy
import os

from typing import TypeVar, Generic, Optional
from dataclasses import dataclass

from .node_walker import NodeWalker
from .numerics import *
from .blender_shader_nodes import *


class MaterialNodeWalker(NodeWalker):

    @dataclass
    class MatSocket:
        exists: bool = False
        connected: bool = False
        image: bpy.types.Image = None
        layer: str = None
        color: Color4F = None
        factor: float = None
        strength: float = None
        scale: Vec2F = None
        child: 'MaterialNodeWalker.MatSocket' = None
        issues: list[str] = None

        def set_value_or_color(self, value: float | tuple):
            if isinstance(value, float):
                self.factor = value
            else:
                self.color = Color4F.from_list4(value)


    @dataclass
    class MatSettings:
        alpha_clip: bool = False
        alpha_clip_threshold: int = 0
        alpha_blend: bool = False
        double_sided: bool = False
        invert_backface_normals: bool = False
        cast_shadows: bool = True

    
    @dataclass
    class MatStage:
        context: 'MaterialNodeWalker'


    def parse_socket_tree(self, socket: 'MaterialNodeWalker.MatSocket'):

        if self.is_node_idname(BeamDetailColor.bl_idname):
            child = MaterialNodeWalker.MatSocket(issues=[])
            child.strength = self.get_float_value("Strength")
            self.get_socket("Detail", child)
            socket.child = child
            socket.color = self.get_color_value("Base")
            self.follow("Base")

        if self.is_node_idname(BeamDetailNormal.bl_idname):
            child = MaterialNodeWalker.MatSocket(issues=[])
            self.get_socket("Detail", child)
            socket.child = child
            self.follow("Base")


        if self.is_node_idname(BeamFactorFloat.bl_idname):
            socket.factor = self.get_float_value("Factor")
            self.follow("Texture Map")

        if self.is_node_idname(BeamFactorColor.bl_idname):
            socket.color = self.get_color_value("Factor")
            self.follow("Texture Map")

        if self.is_node_idname(NodeName.Mix):
            socket.color = self.get_color_value(7)
            self.follow(6)

        if self.is_node_idname(NodeName.VectorMath):
            socket.color = self.get_color_value(1)
            self.follow(0)

        if self.is_node_idname(NodeName.Math):
            socket.factor = self.get_float_value(1)
            self.follow(0)

        if self.is_node_idname(NodeName.NormalMap):
            socket.strength = self.get_float_value("Strength")
            self.follow("Color")


        if self.is_node_idname(NodeName.TexImage):
            socket.image = self.get_image()
            if not self.try_follow("Vector"): return


        if self.is_node_idname(BeamDetailUVScale.bl_idname):
            u = self.get_float_value("Scale U")
            v = self.get_float_value("Scale V")
            socket.scale = Vec2F(u, v)
            self.follow("UV")

        if self.is_node_idname(NodeName.VectorMath):
            scale = self.get_default_value(1)
            socket.scale = Vec2F(scale[0], scale[1])
            self.follow(0)


        if self.is_node_idname(NodeName.UVMap):
            socket.layer = self.current.uv_map


    def get_socket(self, input_key: str | int, socket: 'MaterialNodeWalker.MatSocket' = None) -> 'MaterialNodeWalker.MatSocket':

        if socket is None:
            socket = MaterialNodeWalker.MatSocket(issues=[])

        try:
            input = self.get_input(input_key, False)
            if input is not None:
                socket.exists = True
                socket.color = self.get_color_value(input)
                socket.factor = self.get_float_value(input)
                ctx = self.fork()
                if ctx.try_follow(input_key):
                    socket.connected = True
                    ctx.parse_socket_tree(socket)

        except Exception as e:
            print(e)

        finally:
            return socket


    def parse_stage_recursively(self, stages: list['MaterialNodeWalker.MatStage'] = None):

        if stages is None:
            stages = []

        if self.is_node_idname(BeamStageMix.bl_idname):
            context = self.fork("Overlay")
            self.follow("Base")
            self.parse_stage_recursively(stages)
            context.parse_stage_recursively(stages)
        else:
            stages.append(MaterialNodeWalker.MatStage(self))

        return stages
    

    def parse_mat_settings(self) -> 'MaterialNodeWalker.MatSettings':
        mat = MaterialNodeWalker.MatSettings()
        if self.is_node_idname(BeamMaterial.bl_idname):
            mat.alpha_clip = self.get_float_value(BeamMaterial.Sockets.CLIP) > 0.5
            mat.alpha_clip_threshold = self.get_float_value(BeamMaterial.Sockets.CLIP_T)
            mat.alpha_blend = self.get_float_value(BeamMaterial.Sockets.BLEND) > 0.5
            mat.double_sided = self.get_float_value(BeamMaterial.Sockets.DS) > 0.5
            mat.invert_backface_normals = self.get_float_value(BeamMaterial.Sockets.IBN) > 0.5
            mat.cast_shadows = self.get_float_value(BeamMaterial.Sockets.SHADOWS) > 0.5
            self.try_follow(SocketName.Shader)
        return mat
            

