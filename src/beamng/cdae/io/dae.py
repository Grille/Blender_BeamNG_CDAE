import xml.etree.cElementTree as ET

from numpy.typing import NDArray
from dataclasses import dataclass
from enum import Enum


VERSION = "1.4.1"
NAMESPACE = "http://www.collada.org/2005/11/COLLADASchema"


class Semantic(str, Enum):
    POSITION = "POSITION"
    VERTEX = "VERTEX"
    NORMAL = "NORMAL"
    TEXCOORD = "TEXCOORD"
    COLOR = "COLOR"



class DaeAttributes(str, Enum):
    VERSION = "version"
    XMLNS = "xmlns"


class DaeTag(str, Enum):
    COLLADA = "COLLADA"
    library_geometries = "library_geometries"
    geometry = "geometry"
    mesh = "mesh"
    source = "source"
    float_array = "float_array"
    technique_common = "technique_common"
    accessor = "accessor"
    param = "param"
    vertices = "vertices"
    input = "input"
    triangles = "triangles"
    polylist = "polylist"
    p = "p"
    library_materials = "library_materials"
    material = "material"
    instance_effect = "instance_effect"
    library_effects = "library_effects"
    effect = "effect"
    library_visual_scenes = "library_visual_scenes"
    visual_scene = "visual_scene"
    node = "node"
    instance_geometry = "instance_geometry"
    bind_material = "bind_material"
    instance_material = "instance_material"
    scene = "scene"
    instance_visual_scene = "instance_visual_scene"
    library_animations = "library_animations"
    animation = "animation"
    sampler = "sampler"
    channel = "channel"
    matrix = "matrix"
    def __str__(self):
        return self.value
    


class Geometry:

    class Triangles:

        @dataclass
        class Input:
            semantic: Semantic
            source: str
            offset: int = 0
            set: int = 0
            pass

        def __init__(self):
            self.triangle_count: int = 0
            self.materialName: str = None
            self.indices: NDArray = None
            self.inputs: list[Geometry.Triangles.Input] = []



    def __init__(self):
        self.sources: dict[str, NDArray] = {}
        self.triangles: list[Geometry.Triangles] = []


    def get_array(self, semantic: Semantic, set: int = 0) -> NDArray | None:
        triangles = self.triangles[0]
        for input in triangles.inputs:
            if (input.semantic == semantic and input.set == set):
                return self.sources[input.source]
        return None




class GeometryInstance:

    def __init__(self, name: str, materials: dict[str,str]):
        self.name = name
        self.materials = materials



class Node:

    def __init__(self):
        self.name: str
        self.matrix: NDArray
        self.children: list[Node] = []
        self.geometry: GeometryInstance | None = None



@dataclass
class Material:
    id: str
    name: str



class Collada:

    def __init__(self):
        self.geometries: list[Geometry] = []
        self.materials: list[Material] = []
        self.nodes: list[Node] = []



@dataclass(frozen=True)
class Accessor:
    stride: int
    params: list['Accessor.Param']
    source: str = None
    count: int = 0

    @dataclass(frozen=True)
    class Param:
        name: str
        type: str

    def extend_by_float(self, key: str):
        return Accessor(self.stride + 1, self.params + [Accessor.Param(key, "float")])
    
    @staticmethod
    def create(stride: int, key: str, type: str):
        return Accessor(stride, [Accessor.Param(key, type)])
    
    @staticmethod
    def create_float(key: str):
        return Accessor.create(1, key, "float")



class Accessors:
    VEC1 = Accessor.create_float("X")
    VEC2 = VEC1.extend_by_float("Y")
    VEC3 = VEC2.extend_by_float("Z")
    VEC4 = VEC3.extend_by_float("W")
    TIME = Accessor.create_float("TIME")
    TRANSFORM = Accessor.create(16, "TRANSFORM", "float4x4")

