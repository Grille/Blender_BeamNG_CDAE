import bpy
import os

from typing import TypeVar, Generic, Optional
from dataclasses import dataclass

from .node_walker import NodeWalker
from .numerics import *
from .blender_shader_nodes import *
from .material import Material


class MaterialNodeWalker(NodeWalker):

    @dataclass
    class PalleteFlags:
        base_color: bool
        clear_coat: bool
        clear_coat_roughness: bool
        metallic: bool
        roughness: bool


    @dataclass
    class MatSocketInfo:
        exists: bool = False
        connected: bool = False
        image: bpy.types.Image = None
        layer: str = None
        color: Color4F = None
        enabled_vc: bool = False
        enabled_ic: bool = False
        factor: float = None
        strength: float = None
        scale: Vec2F = None
        child: 'MaterialNodeWalker.MatSocketInfo' = None
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
    class MatStageInfo:
        context: 'MaterialNodeWalker'


    def parse_socket_tree(self, socket: 'MaterialNodeWalker.MatSocketInfo'):

        if self.is_node_idname(BeamFactorFloat):
            socket.factor = self.get_float_value("Factor")
            self.follow("Texture Map")

        if self.is_node_idname(BeamFactorColor):
            socket.enabled_vc = self.is_linked(SocketName.VertexColor)
            socket.enabled_ic = self.is_linked(SocketName.InstanceColor)
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


        if self.is_node_idname(BeamDetailColor):
            child = MaterialNodeWalker.MatSocketInfo(issues=[])
            child.strength = self.get_float_value("Strength")
            self.get_socket("Detail", child)
            socket.child = child
            self.follow("Base")

        if self.is_node_idname(BeamDetailNormal):
            child = MaterialNodeWalker.MatSocketInfo(issues=[])
            self.get_socket("Detail", child)
            socket.child = child
            self.follow("Base")


        if self.is_node_idname(NodeName.NormalMap):
            socket.strength = self.get_float_value("Strength")
            self.follow("Color")


        if self.is_node_idname(NodeName.TexImage):
            socket.image = self.get_image()
            if not self.try_follow("Vector"): return


        if self.is_node_idname(BeamDetailUVScale):
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


    def get_socket(self, input_key: str | int, socket: 'MaterialNodeWalker.MatSocketInfo' = None) -> 'MaterialNodeWalker.MatSocketInfo':

        if socket is None:
            socket = MaterialNodeWalker.MatSocketInfo(issues=[])

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
        

    def try_get_version_hint(self) -> float:

        if self.is_node_idname(BeamBDSF10Basic):
            return 1.0
        
        elif self.is_node_idname(BeamBSDF15):
            return 1.5
        
        elif self.is_node_idname(BeamStageMix):
            return 1.5
        
        return 0.0
    

    def try_get_reflect_hint(self) -> bool:

        if self.is_node_idname(BeamBDSF10Basic):
            return self.get_bool_value(SocketName.ReflectionEnabled)
        
        elif self.is_node_idname(BeamBSDF15):
            return True
        
        return False
        

    def get_any_socket(self, keys: list[str|int]):
        if not isinstance(keys, list):
            return self.get_socket(keys)
        if len(keys) == 0:
            raise ValueError()
        for key in keys:
            socket = self.get_socket(key)
            if socket.exists:
                return socket
        return socket


    def parse_stages_recursively(self, stages: list['MaterialNodeWalker.MatStageInfo'] = None):

        if stages is None:
            stages = []

        if self.is_node_idname(BeamStageMix):
            context = self.fork("Overlay")
            self.follow("Base")
            self.parse_stages_recursively(stages)
            context.parse_stages_recursively(stages)
        else:
            stages.append(MaterialNodeWalker.MatStageInfo(self))

        return stages
    

    def is_collider(self):
        return self.is_node_idname(BeamBSDFCollision)
    

    def try_parse_mat_settings(self, mat: Material):

        if not self.is_node_idname(BeamMaterial):
            return
        
        alpha_clip = self.get_float_value(BeamMaterial.Sockets.CLIP) > 0.5
        alpha_clip_threshold = self.get_float_value(BeamMaterial.Sockets.CLIP_T)
        alpha_blend = self.get_float_value(BeamMaterial.Sockets.BLEND) > 0.5
        double_sided = self.get_float_value(BeamMaterial.Sockets.DOUBLE_SIDED) > 0.5
        invert_backface_normals = self.get_float_value(BeamMaterial.Sockets.INVERT_BACKFACE_NORMALS) > 0.5
        cast_shadows = self.get_float_value(BeamMaterial.Sockets.SHADOWS) > 0.5

        mat.alpha_test = alpha_clip
        mat.alpha_ref = int(alpha_clip_threshold * 255)
        mat.translucent = alpha_blend
        mat.translucent_blend_op = "PreMulAlpha" if alpha_blend else None
        mat.double_sided = double_sided
        mat.invert_backface_normals = double_sided and invert_backface_normals
        mat.cast_shadows = cast_shadows

        self.try_follow(SocketName.Shader)
            

