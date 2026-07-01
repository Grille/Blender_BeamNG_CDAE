import mathutils
import xml.etree.cElementTree as ET
import numpy as np

from numpy.typing import NDArray
from dataclasses import dataclass
from ....enums import StrEnum
from ...numerics import *


VERSION = "1.4.1"
NAMESPACE = "http://www.collada.org/2005/11/COLLADASchema"



class Semantic(StrEnum):
    POSITION = "POSITION"
    VERTEX = "VERTEX"
    NORMAL = "NORMAL"
    TEXCOORD = "TEXCOORD"
    COLOR = "COLOR"



class DaeAttributes(StrEnum):
    NAME = "name"
    VERSION = "version"
    XMLNS = "xmlns"
    MATERIAL = "material"
    COUNT = "count"
    STRIDE = "stride"
    METER = "meter"



class DaeTag(StrEnum):
    COLLADA = "COLLADA"
    asset = "asset"
    unit = "unit"
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
    vcount = "vcount"
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
    


class Geometry:

    @dataclass
    class Source:
        array: NDArray
        element_count: int
        stride: int


        def shaped(self) -> NDArray[np.float32]:
            return self.array.reshape((self.element_count, self.stride))



    class Triangles:

        @dataclass
        class Input:
            semantic: Semantic
            source: str
            offset: int = 0
            set: int = 0



        @property
        def stride(self):
            return max(input.offset for input in self.inputs) + 1


        def __init__(self, owner: 'Geometry'):
            self.owner = owner
            self.triangle_count: int = 0
            self.material_name: str = None
            self.indices: NDArray[np.int32] = None
            self.inputs: list['Geometry.Triangles.Input'] = []


        def get_input(self, semantic: Semantic, set: int = 0) -> Input | None:
            for input in self.inputs:
                if (input.semantic == semantic and input.set == set):
                    return input
            return None
        

        def get_indexed_array(self, semantic: Semantic, set: int = 0) -> NDArray[np.float32] | None:

            input = self.get_input(semantic, set)
            if input is None:
                return None
            
            source = self.owner.sources.get(input.source)
            if source is None:
                return None

            data = source.shaped()

            if semantic == Semantic.TEXCOORD:
                data = data[:, :2]

            # extract this attribute's index stream
            idx = self.indices[input.offset::self.stride]

            return data[idx]
        

    def __init__(self):
        self.name: str
        self.sources: dict[str, 'Geometry.Source'] = {}
        self.triangles: list['Geometry.Triangles'] = []



class GeometryInstance:

    def __init__(self, url: str, materials: dict[str,str]):
        self.url = url
        self.materials = materials



class Node:

    def __init__(self):
        self.name: str
        self.matrix: DaeMatrix | None
        self.children: dict[str, Node] = {}
        self.geometry_instance: GeometryInstance | None = None



@dataclass
class Material:
    name: str



class Collada:

    def __init__(self):
        self.unit_meter: float = 1.0
        self.geometries: dict[str, Geometry] = {}
        self.materials: dict[str, Material] = {}
        self.nodes: dict[str, Node] = {}



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



class DaeMatrix:

    def __init__(self, values: NDArray[np.float32]):
        self.values = values


    @staticmethod
    def from_matrix(matrix: mathutils.Matrix):
        return DaeMatrix(np.array(matrix, dtype=np.float32).flatten(order='F'))
    

    def to_matrix(self):
        return mathutils.Matrix(np.array(self.values, dtype=np.float32).reshape((4, 4), order='F'))


    @staticmethod
    def from_cdae(quat: Quat4F, location: Vec3F):
        matrix = quat.to_collada_quaternion().to_matrix().to_4x4()
        matrix.translation = location.tuple3
        return DaeMatrix.from_matrix(matrix)


