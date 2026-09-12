import mathutils
import xml.etree.cElementTree as ET
#import numpy as np

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



    @dataclass
    class Triangles:
        owner: Geometry
        triangle_count: int
        material_name: str
        indices: NDArray[np.int32]
        inputs: list['Geometry.Triangles.Input']


        @dataclass
        class Input:
            semantic: Semantic
            source: str
            offset: int = 0
            set: int = 0


        @property
        def stride(self):
            return max(input.offset for input in self.inputs) + 1


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

    @dataclass(frozen=True)
    class Param:
        name: str
        type: str

    def extend(self, key: str, type: str = "float"):
        return Accessor(self.stride + 1, self.params + [Accessor.Param(key, type)])
    
    @staticmethod
    def create(key: str, type: str = "float", stride: int = 1):
        return Accessor(stride, [Accessor.Param(key, type)])



class Accessors:
    VEC1 = Accessor.create("X")
    VEC2 = VEC1.extend("Y")
    VEC3 = VEC2.extend("Z")
    VEC4 = VEC3.extend("W")
    TIME = Accessor.create("TIME")
    TRANSFORM = Accessor.create("TRANSFORM", "float4x4", 16)



class DaeMatrix:

    def __init__(self, values: NDArray[np.float32]):
        self.values = values


    @staticmethod
    def from_matrix(matrix: mathutils.Matrix):
        return DaeMatrix(np.array(matrix, dtype=np.float32).flatten(order='F'))
    

    def to_matrix(self):
        array = np.array(self.values, dtype=np.float32).reshape((4, 4), order='F')
        return mathutils.Matrix(array) # pyright: ignore[reportArgumentType]


    @staticmethod
    def from_cdae(quat: Quat4F, location: Vec3F):
        matrix = quat.to_collada_quaternion().to_matrix().to_4x4()
        matrix.translation = location.tuple3
        return DaeMatrix.from_matrix(matrix)


    @staticmethod
    def flatten_matrices(matrices: Sequence[DaeMatrix]) -> list[float]:
        return [v for mat in matrices for v in mat.values]


