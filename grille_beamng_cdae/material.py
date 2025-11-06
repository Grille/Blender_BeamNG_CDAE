import os

from typing import TypeVar, Generic, Optional

from .numerics import *
from .blender_enums import *



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


    def __init__(self, prefix: str, dict: dict):
        self.prefix = prefix
        self.dict = dict



class Stage:

    use_anisotropic: bool = DictProperty("useAnisotropic")
    vertex_color: bool = DictProperty("vertColor")
    instance_diffuse: bool = DictProperty("instanceDiffuse")


    def __init__(self, basedict: dict[str, any] = None):
        self.prefix = ""
        self.dict = {} if basedict is None else basedict

        self.sockets: list[Socket] = []

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


    def move(self, src: str, dst: str):
        value = self.dict.pop(src, None)
        if value is not None:
            self.dict[dst] = value


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
    translucent_blend_op: str = DictProperty("translucentBlendOp") #"PreMulAlpha"
    translucent_zwrite: bool = DictProperty("translucentZWrite")
    translucent_recv_shadows: bool = DictProperty("translucentRecvShadows")
    double_sided: bool = DictProperty("doubleSided")
    invert_backface_normals: bool = DictProperty("invertBackFaceNormals")
    cast_shadows: bool = DictProperty("castShadows")
    dynamic_cubemap: bool = DictProperty("dynamicCubemap")
    cubemap: str = DictProperty("cubemap")


    def __init__(self, basedict: dict[str, any] = None):
        self.dict = {} if basedict is None else basedict
        self.prefix = ""

        if Material.STAGES_KEY not in self.dict:
            self.dict[Material.STAGES_KEY] = [{},{},{},{}]

        raw_stages: list[dict] = self.dict[Material.STAGES_KEY]
        self.stages = [Stage(raw_stages[0]), Stage(raw_stages[1]), Stage(raw_stages[2]), Stage(raw_stages[3])]


    def add_texture_names_to(self, target: set[str]):
        for stage in self.stages:
            stage.add_texture_names_to(target)


    def add_relpath(self, relpath):
        for stage in self.stages:
            stage.add_relpath(relpath)