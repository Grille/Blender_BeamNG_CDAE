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


class Socket:
    
    factor: float | list[float] = DictProperty("Factor")
    strength: float = DictProperty("MapStrength")
    bcm_strength: float = DictProperty("BaseColorMapStrength")
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


    def parse_socket(self, src: NodeWalker.Socket, set: ParserSettings):

        if set.color_enabled and src.color:
            self.factor = src.color.to_list()
        if set.factor_enabled and src.factor:
            self.factor = src.factor
        if src.strength:
            self.strength = src.strength

        if src.image:
            self.map = src.image.name

        if src.scale:
            self.scale = [src.scale.x, src.scale.y]

        if src.layer:
            self.use_uv = 1 if set.uv1hint in src.layer else 0


class Stage:

    use_anisotropic: bool = DictProperty("useAnisotropic")


    def __init__(self, basedict: dict[str, any] = None):
        self.prefix = ""
        self.dict = {} if basedict is None else basedict

        self.base_color = Socket("baseColor", self.dict)
        self.detail = Socket("detail", self.dict)
        self.metallic = Socket("metallic", self.dict)
        self.normal = Socket("normal", self.dict)
        self.detail_normal = Socket("detailNormal", self.dict)
        self.roughness = Socket("roughness", self.dict)
        self.opacity = Socket("opacity", self.dict)
        self.ambient_occlusion = Socket("ambientOcclusion", self.dict)


    def add_texture_names_to(self, target: set[str]):
        def try_add(value: str | None): 
            if value is not None: target.add(value)
        try_add(self.base_color.map)
        try_add(self.metallic.map)
        try_add(self.normal.map)
        try_add(self.roughness.map)
        try_add(self.opacity.map)


    def parse_shader_node(self, head: NodeWalker.StageHead, uv1hint: str):
        ctx = head.context

        COLOR = Socket.ParserSettings(uv1hint, True, False)
        FLOAT = Socket.ParserSettings(uv1hint, False, True)
        MAP = Socket.ParserSettings(uv1hint, False, False)

        base_color = ctx.get_socket("Base Color")
        self.base_color.parse_socket(base_color, COLOR)

        if base_color.child:
            self.detail.parse_socket(base_color.child, MAP)
            self.detail.bcm_strength = self.detail.strength

        metallic = ctx.get_socket("Metallic")
        self.metallic.parse_socket(metallic, FLOAT)

        roughness = ctx.get_socket("Roughness")
        self.roughness.parse_socket(roughness, FLOAT)

        normal = ctx.get_socket("Normal")
        self.normal.parse_socket(normal, MAP)

        if normal.child:
            self.detail_normal.parse_socket(normal.child, MAP)

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
        self.stages = [Stage(raw_stages[0]), Stage(raw_stages[1]), Stage(raw_stages[2]), Stage(raw_stages[3])]


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
        ctx.find_output(bmat.node_tree.nodes)
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