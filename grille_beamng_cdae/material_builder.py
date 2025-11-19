import bpy

from dataclasses import dataclass

from .blender_material_properties import MaterialProperties
from.material_builder_nw import MaterialNodeWalker
from .material import *


@dataclass
class SocketParserSettings:
    uv1hint: str
    color_enabled: bool
    factor_enabled: bool
    map_enabled: bool = True
    color_is_vec3: bool = False



class MaterialBuilder:

    def __init__(self, default_version = 1.5):
        self.material = Material()
        self.default_version = default_version
        self.uv1_hint = "1"


    def parse_socket(self, socket: Socket, src: MaterialNodeWalker.MatSocketInfo, set: SocketParserSettings):

        if set.color_enabled and src.color is not None:
            socket.factor = src.color.srgb.tuple3 if set.color_is_vec3 else src.color.srgb.tuple4
        if set.factor_enabled and src.factor is not None:
            socket.factor = src.factor
        if src.strength is not None:
            socket.strength = src.strength

        if set.map_enabled and src.image is not None:
            socket.map = src.image.name

        if socket.map is not None and socket.factor is None:
            socket.factor = 1.0

        if src.scale is not None:
            socket.scale = [src.scale.x, src.scale.y]

        if src.layer is not None:
            socket.use_uv = 1 if set.uv1hint.lower() in src.layer.lower() else 0


    def parse_stage(self, stage: Stage, info: MaterialNodeWalker.MatStageInfo):

        COLOR4 = SocketParserSettings(self.uv1_hint, True, False)
        COLOR3 = SocketParserSettings(self.uv1_hint, True, False, color_is_vec3=True)
        FLOAT = SocketParserSettings(self.uv1_hint, False, True)
        #FLOAT_NOMAP = SocketParserSettings(self.uv1_hint, False, True, map_enabled=False)
        MAP_ONLY = SocketParserSettings(self.uv1_hint, False, False)

        stage.use_anisotropic = True
        ctx = info.context

        self.material.version = ctx.try_get_version_hint()
        self.material.dynamic_cubemap = ctx.try_get_reflect_hint()

        def parse_socket(socket: Socket, socket_name: str | list[str], settings: SocketParserSettings, detail: Socket = None):
            nw_socket = ctx.get_any_socket(socket_name)
            self.parse_socket(socket, nw_socket, settings)
            if detail and nw_socket.child:
                self.parse_socket(detail, nw_socket.child, MAP_ONLY)
            return nw_socket

        stage.color.factor = (1,1,1,1)

        socket = parse_socket(stage.color, [SocketName.ColorHDR, SocketName.Color, SocketName.BaseColor], COLOR4, stage.detail)
        stage.move("baseColorMapUseUV", "diffuseMapUseUV")
        stage.move("detailMapStrength", "detailBaseColorMapStrength")
        stage.vertex_color = socket.enabled_vc
        stage.instance_diffuse = socket.enabled_ic
        
        basealpha = ctx.get_socket(SocketName.BaseAlpha)
        if basealpha.factor is not None:
            stage.color.factor = stage.color.factor[:3] + (basealpha.factor,)

        parse_socket(stage.metallic, SocketName.Metallic, FLOAT)

        parse_socket(stage.roughness, SocketName.Roughness, FLOAT)

        parse_socket(stage.normal, SocketName.Normal, MAP_ONLY, stage.detail_normal)
        stage.move("detailNormalScale", "detailScale")
        stage.move("detailNormalMapUseUV", "normalDetailMapUseUV")

        parse_socket(stage.opacity, SocketName.Alpha, FLOAT)

        parse_socket(stage.ambient_occlusion, SocketName.AmbientOcclusion, FLOAT)
        
        parse_socket(stage.palette, SocketName.Palette, MAP_ONLY)

        socket = parse_socket(stage.emissive, SocketName.Emissive, COLOR3)
        stage.vertex_emissive = socket.enabled_vc
        stage.instance_emissive = socket.enabled_ic

        parse_socket(stage.clear_coat, SocketName.ClearCoat, FLOAT)

        parse_socket(stage.clear_coat_roughness, SocketName.ClearCoatRoughness, FLOAT)


    def parse_node_tree(self, ctx: MaterialNodeWalker):

        mat = self.material

        if ctx.is_collider():
            mat.version = 1.0
            mat.stages[0].color.factor = [1,0,1,0]
            mat.alpha_test = True
            mat.alpha_ref = 255
            mat.cast_shadows = False
            return
        
        ctx.try_parse_mat_settings(mat)

        stage_infos = ctx.parse_stages_recursively()
        mat.active_layers = len(stage_infos)
        for i, info in enumerate(stage_infos):
            self.parse_stage(mat.stages[i], info)


    def build_from_bmat(self, bmat: bpy.types.Material):

        mat = self.material
        mat.name = bmat.name
        mat.map_to = mat.name
        mat.class_name = "Material"
        mat.ground_type = MaterialProperties.get_ground_type(bmat)

        if bmat.node_tree is not None:
            
            ctx = MaterialNodeWalker()
            ctx.find_material_output(bmat.node_tree.nodes)
            ctx.follow(SocketName.Surface)
            self.parse_node_tree(ctx)

        if mat.version == 0.0:
            mat.version = self.default_version

        return mat
    
