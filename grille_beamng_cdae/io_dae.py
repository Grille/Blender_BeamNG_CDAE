from numpy.typing import NDArray
from dataclasses import dataclass
from enum import Enum


class Semantic(str, Enum):
    VERTEX = "VERTEX"
    NORMAL = "NORMAL"
    TEXCOORD = "TEXCOORD"
    COLOR = "COLOR"



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
            self.count: int = 0
            self.mat: str = None
            self.indices: NDArray = None
            self.inputs: list[Geometry.Triangles.Input] = []



    def __init__(self):
        self.sources: dict[str, NDArray] = {}
        self.triangles: list[Geometry.Triangles] = []



class Node:

    def __init__(self):
        self.name: str
        self.children: list[Node] = []
        self.geometry: str



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
        return Accessor.create(0, key, "float")



class Accessors:
    VEC1 = Accessor.create_float("X")
    VEC2 = VEC1.extend_by_float("Y")
    VEC3 = VEC2.extend_by_float("Z")
    VEC4 = VEC3.extend_by_float("W")
    TIME = Accessor.create_float("TIME")
    TRANSFORM = Accessor.create(16, "TRANSFORM", "float4x4")

