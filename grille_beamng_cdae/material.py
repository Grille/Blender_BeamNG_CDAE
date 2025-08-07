import bpy
import os

from typing import TypeVar, Generic, Optional
from dataclasses import dataclass

from .node_walker import NodeWalker
from .blender_material_properties import MaterialProperties
from .numerics import *
from .blender_enums import *
from .material_nw import MaterialNodeWalker



T = TypeVar('T')
class DictProperty(Generic[T]):

    def __init__(self, key: str):
        self.key = key


    def __get__(self, instance: 'Material', owner) -> Optional[T]:
        return instance.dict.get(f"{instance.prefix}{self.key}", None)


    def __set__(self, instance: 'Material', value: Optional[T]):
        if value is None:
            instance.dict.pop(f"{instance.prefix}{self.key}", None)
        else:
            instance.dict[f"{instance.prefix}{self.key}"] = value



class Socket:
    
    factor: float | list[float] = DictProperty("Factor")
    strength: float = DictProperty("MapStrength")
    use_uv: int = DictProperty("MapUseUV")
    map: str = DictProperty("Map")
    scale: list[float] = DictProperty("Scale")


    @dataclass
    class ParserSettings:
        uv1hint: str
        color_enabled: bool
        factor_enabled: bool
        map_enabled: bool = True
        color_is_vec3: bool = False


    def __init__(self, prefix: str, dict: dict):
        self.prefix = prefix
        self.dict = dict


    def parse_socket(self, src: MaterialNodeWalker.MatSocket, set: ParserSettings):

        if set.color_enabled and src.color is not None:
            self.factor = src.color.srgb.tuple3 if set.color_is_vec3 else src.color.srgb.tuple4
        if set.factor_enabled and src.factor is not None:
            self.factor = src.factor
        if src.strength is not None:
            self.strength = src.strength

        if set.map_enabled and src.image is not None:
            self.map = src.image.name

        if self.map is not None and self.factor is None:
            self.factor = 1.0

        if src.scale is not None:
            self.scale = [src.scale.x, src.scale.y]

        if src.layer is not None:
            self.use_uv = 1 if set.uv1hint in src.layer else 0


    def move(self, src: str, dst: str):
        value = self.dict.pop(src, None)
        if value is not None:
            self.dict[dst] = value



class Stage:

    use_anisotropic: bool = DictProperty("useAnisotropic")
    vertex_color: bool = DictProperty("vertColor")


    def __init__(self, basedict: dict[str, any] = None):
        self.prefix = ""
        self.dict = {} if basedict is None else basedict

        self.sockets = []

        def CreateSocket(name: str):
            socket = Socket(name, self.dict)
            self.sockets.append(socket)
            return socket

        self.color = CreateSocket("baseColor")
        self.detail = CreateSocket("detail")
        self.metallic = CreateSocket("metallic")
        self.normal = CreateSocket("normal")
        self.detail_normal = CreateSocket("detailNormal")
        self.roughness = CreateSocket("roughness")
        self.opacity = CreateSocket("opacity")
        self.ambient_occlusion = CreateSocket("ambientOcclusion")
        self.emissive = CreateSocket("emissive")
        self.clear_coat = CreateSocket("clearCoat")
        self.clear_coat_roughness = CreateSocket("clearCoatRoughness")


    def add_texture_names_to(self, target: set[str]):
        for socket in self.sockets:
            if socket.map is not None: target.add(socket.map)


    def add_relpath(self, relpath):
        for socket in self.sockets:
            if socket.map is not None and relpath != ".":
                socket.map = os.path.join(relpath, socket.map)


    def parse_shader_node(self, head: MaterialNodeWalker.MatStage, uv1hint: str):
        ctx = head.context

        COLOR4 = Socket.ParserSettings(uv1hint, True, False)
        COLOR3 = Socket.ParserSettings(uv1hint, True, False, color_is_vec3=True)
        FLOAT = Socket.ParserSettings(uv1hint, False, True)
        MAP = Socket.ParserSettings(uv1hint, False, False)

        color = ctx.get_socket(SocketName.ColorHDR)
        if not color.exists:
            ctx.get_socket(SocketName.Color, color)
        if not color.exists:
            ctx.get_socket(SocketName.BaseColor, color)
        self.color.parse_socket(color, COLOR4)
        self.color.move("baseColorMapUseUV", "diffuseMapUseUV")

        if color.child:
            self.detail.parse_socket(color.child, MAP)
            self.detail.move("detailMapStrength", "detailBaseColorMapStrength")

        vert = ctx.get_socket(SocketName.VertexColor)
        self.vertex_color = vert.connected

        metallic = ctx.get_socket(SocketName.Metallic)
        self.metallic.parse_socket(metallic, FLOAT)

        roughness = ctx.get_socket(SocketName.Roughness)
        self.roughness.parse_socket(roughness, FLOAT)

        normal = ctx.get_socket(SocketName.Normal)
        self.normal.parse_socket(normal, MAP)

        if normal.child:
            self.detail_normal.parse_socket(normal.child, MAP)
            self.detail_normal.move("detailNormalMapUseUV", "normalDetailMapUseUV")

        normal = ctx.get_socket(SocketName.Alpha)
        self.opacity.parse_socket(normal, FLOAT)

        ao = ctx.get_socket(SocketName.AmbientOcclusion)
        self.ambient_occlusion.parse_socket(ao, FLOAT)

        emissive = ctx.get_socket(SocketName.Emissive)
        self.emissive.parse_socket(emissive, COLOR3)

        cc = ctx.get_socket(SocketName.ClearCoat)
        self.clear_coat.parse_socket(cc, FLOAT)

        ccr = ctx.get_socket(SocketName.ClearCoatRoughness)
        self.clear_coat_roughness.parse_socket(ccr, FLOAT)


class Material:

    STAGES_KEY = "Stages"

    name: str = DictProperty("name")
    class_name: str = DictProperty("class")
    ground_type: str = DictProperty("groundType")
    map_to: str = DictProperty("mapTo")

    version: float = DictProperty("version")
    active_layers: int = DictProperty("activeLayers")
    
    alpha_test: bool = DictProperty("alphaTest")
    alpha_ref: int = DictProperty("alphaRef")
    translucent: bool = DictProperty("translucent")
    translucent_blend_op: str = DictProperty("translucentBlendOp")
    double_sided: bool = DictProperty("doubleSided")
    invert_backface_normals: bool = DictProperty("invertBackFaceNormals")
    cast_shadows: bool = DictProperty("castShadows")
    translucent_zwrite: bool = DictProperty("translucentZWrite")
    translucent_recv_shadows: bool = DictProperty("translucentRecvShadows")
    dynamic_cubemap: bool = DictProperty("dynamicCubemap")
    cubemap: str = DictProperty("cubemap")


    def __init__(self, basedict: dict[str, any] = None):
        self.dict = {} if basedict is None else basedict
        self.prefix = ""

        if Material.STAGES_KEY not in self.dict:
            self.dict[Material.STAGES_KEY] = [{},{},{},{}]

        raw_stages: list[dict] = self.dict[Material.STAGES_KEY]
        self.stages = [Stage(raw_stages[0]), Stage(raw_stages[1]), Stage(raw_stages[2]), Stage(raw_stages[3])]


    @classmethod
    def from_bmat(cls, bmat: bpy.types.Material, version: float):
        material = cls()

        material.name = bmat.name
        material.map_to = material.name
        material.class_name = "Material"
        material.version = version
        material.ground_type = getattr(bmat, MaterialProperties.GROUND_TYPE)
        uv1hint = getattr(bmat, MaterialProperties.UV1_HINT)

        stage0 = material.stages[0]
        stage0.use_anisotropic = True

        ctx = MaterialNodeWalker()
        ctx.find_material_output(bmat.node_tree.nodes)
        ctx.follow("Surface")

        settings = ctx.parse_mat_settings()
        material.alpha_test = settings.alpha_clip
        material.alpha_ref = int(settings.alpha_clip_threshold * 255)
        material.translucent = settings.alpha_blend
        if material.translucent: material.translucent_blend_op = "PreMulAlpha"
        material.double_sided = settings.double_sided
        material.invert_backface_normals = settings.double_sided and settings.invert_backface_normals
        material.cast_shadows = settings.cast_shadows

        heads = ctx.parse_stage_recursively()

        material.active_layers = len(heads)
        for i, head in enumerate(heads):
            material.stages[i].parse_shader_node(head, uv1hint)

        return material
    

    def add_texture_names_to(self, target: set[str]):
        for stage in self.stages:
            stage.add_texture_names_to(target)


    def add_relpath(self, relpath):
        for stage in self.stages:
            stage.add_relpath(relpath)