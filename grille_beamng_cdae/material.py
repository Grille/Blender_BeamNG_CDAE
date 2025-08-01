import bpy

from typing import TypeVar, Generic, Optional
from dataclasses import dataclass

from .node_walker import NodeWalker
from .blender_material_properties import MaterialProperties

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


    


class SocketV15:
    
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


    def __init__(self, prefix: str, dict: dict):
        self.prefix = prefix
        self.dict = dict


    def parse_socket(self, src: NodeWalker.MatSocket, set: ParserSettings):

        if set.color_enabled and src.color is not None:
            self.factor = src.color.srgb.list4
        if set.factor_enabled and src.factor is not None:
            self.factor = src.factor
        if src.strength is not None:
            self.strength = src.strength

        if src.image is not None:
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



class StageV15:

    use_anisotropic: bool = DictProperty("useAnisotropic")


    def __init__(self, basedict: dict[str, any] = None):
        self.prefix = ""
        self.dict = {} if basedict is None else basedict

        self.base_color = SocketV15("baseColor", self.dict)
        self.detail = SocketV15("detail", self.dict)
        self.metallic = SocketV15("metallic", self.dict)
        self.normal = SocketV15("normal", self.dict)
        self.detail_normal = SocketV15("detailNormal", self.dict)
        self.roughness = SocketV15("roughness", self.dict)
        self.opacity = SocketV15("opacity", self.dict)
        self.ambient_occlusion = SocketV15("ambientOcclusion", self.dict)


    def add_texture_names_to(self, target: set[str]):
        def try_add(value: str | None): 
            if value is not None: target.add(value)
        try_add(self.base_color.map)
        try_add(self.detail.map)
        try_add(self.metallic.map)
        try_add(self.normal.map)
        try_add(self.detail_normal.map)
        try_add(self.roughness.map)
        try_add(self.opacity.map)
        try_add(self.ambient_occlusion.map)


    def parse_shader_node(self, head: NodeWalker.MatStage, uv1hint: str):
        ctx = head.context

        COLOR = SocketV15.ParserSettings(uv1hint, True, False)
        FLOAT = SocketV15.ParserSettings(uv1hint, False, True)
        MAP = SocketV15.ParserSettings(uv1hint, False, False)

        base_color = ctx.get_socket("Base Color")
        if not base_color.exists:
            ctx.get_socket("Color", base_color)
        self.base_color.parse_socket(base_color, COLOR)
        self.base_color.move("baseColorMapUseUV", "diffuseMapUseUV")

        if base_color.child:
            self.detail.parse_socket(base_color.child, MAP)
            self.detail.move("detailMapStrength", "detailBaseColorMapStrength")

        metallic = ctx.get_socket("Metallic")
        self.metallic.parse_socket(metallic, FLOAT)

        roughness = ctx.get_socket("Roughness")
        self.roughness.parse_socket(roughness, FLOAT)

        normal = ctx.get_socket("Normal")
        self.normal.parse_socket(normal, MAP)

        if normal.child:
            self.detail_normal.parse_socket(normal.child, MAP)
            self.detail_normal.move("detailNormalMapUseUV", "normalDetailMapUseUV")

        normal = ctx.get_socket("Alpha")
        self.opacity.parse_socket(normal, FLOAT)

        ao = ctx.get_socket("Ambient Occlusion")
        self.ambient_occlusion.parse_socket(ao, FLOAT)


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

    def __init__(self, basedict: dict[str, any] = None):
        self.dict = {} if basedict is None else basedict
        self.prefix = ""

        if Material.STAGES_KEY not in self.dict:
            self.dict[Material.STAGES_KEY] = [{},{},{},{}]

        raw_stages: list[dict] = self.dict[Material.STAGES_KEY]
        self.stages = [StageV15(raw_stages[0]), StageV15(raw_stages[1]), StageV15(raw_stages[2]), StageV15(raw_stages[3])]


    @classmethod
    def from_bmat(cls, bmat: bpy.types.Material):
        material = cls()

        material.name = bmat.name
        material.map_to = material.name
        material.class_name = "Material"
        material.version = 1.0 if getattr(bmat, MaterialProperties.VERSION) == "1.0" else 1.5
        material.ground_type = getattr(bmat, MaterialProperties.GROUND_TYPE)
        uv1hint = getattr(bmat, MaterialProperties.UV1_HINT)

        stage0 = material.stages[0]
        stage0.use_anisotropic = True

        ctx = NodeWalker()
        ctx.find_material_output(bmat.node_tree.nodes)
        ctx.follow("Surface")

        settings = ctx.parse_mat_settings()
        material.alpha_test = settings.alpha_clip
        material.alpha_ref = int(settings.alpha_clip_threshold * 255)
        material.translucent = settings.alpha_blend
        if material.translucent: material.translucent_blend_op = "PreMulAlpha"
        material.double_sided = settings.double_sided
        material.invert_backface_normals = settings.invert_backface_normals
        material.cast_shadows = settings.cast_shadows

        heads = ctx.parse_stage_recursively()

        material.active_layers = len(heads)
        for i, head in enumerate(heads):
            material.stages[i].parse_shader_node(head, uv1hint)

        return material
    

    def add_texture_names_to(self, target: set[str]):
        for stage in self.stages:
            stage.add_texture_names_to(target)