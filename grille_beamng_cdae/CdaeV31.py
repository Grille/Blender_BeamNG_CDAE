import struct
import numpy as np

from enum import Enum
from io import BufferedReader

from .msgpack_reader import MsgpackReader
from .numerics import *


class CdaeV31:

    class PackedVector:

        def __init__(self):
            self.element_count: int
            self.element_size: int
            self.data: bytes


        def __iter__(self):
            for i in range(self.element_count):
                yield self[i]


        def __getitem__(self, index):
            start = index * self.element_size
            end = start + self.element_size
            return self.data[start:end]
        

        def to_numpy_buffer(self, type, size = 1):
            return np.frombuffer(self.data, type, self.element_count * size)



    class Node:

        def __init__(self):

            self.nameIndex: int = 0
            self.parentIndex: int = 0
            self.firstObject: int = 0
            self.firstChild: int = 0
            self.nextSibling: int = 0



    class Object:

        def __init__(self):

            self.nameIndex: int = 0
            self.numMeshes: int = 0
            self.startMeshIndex: int = 0
            self.nodeIndex: int = 0
            self.nextSibling: int = 0
            self.firstDecal: int = 0

    

    class ObjectState:
        
        def __init__(self):

            self.vis: float
            self.frameIndex: int
            self.matFrameIndex: int



    class Trigger:

        def __init__(self):
            
            self.state: int
            self.pos: float



    class Detail:

        def __init__(self):

            self.nameIndex: int
            self.subShapeNum: int
            self.objectDetailNum: int
            self.size: float
            self.averageError: float
            self.maxError: float
            self.polyCount: int
            self.bbDimension: int
            self.bbDetailLevel: int
            self.bbEquatorSteps: int
            self.bbPolarSteps: int
            self.bbPolarAngle: float
            self.bbIncludePoles: int



    class MeshType(Enum):

        STANDARD = 0
        SKIN = 1
        DECAL = 2
        SORTED = 3
        NULL = 4



    class Mesh:

        class DrawRegion:

            class Info:
                def __init__(self):
                    pass



            def __init__(self):

                self.elements_start: int
                self.elements_count: int
                self.info: int


            def decode_info(self) -> Info:
                pass


            def encode_info(self, info: Info):
                pass



        def __init__(self):

            self.type: CdaeV31.MeshType = 0

            self.numFrames: int = 0
            self.numMatFrames: int = 0
            self.parentMesh: int = 0
            self.bounds: Box6F = Box6F.create_empty()
            self.center: Vec3F = Vec3F.create_empty()
            self.radius: float = 0.0

            self.verts: CdaeV31.PackedVector #vtx vec3
            self.tverts0: CdaeV31.PackedVector #vtx vec2
            self.tverts1: CdaeV31.PackedVector #vtx vec2
            self.colors: CdaeV31.PackedVector #vtx int/rgba
            self.norms: CdaeV31.PackedVector #vtx vec3
            self.encodedNorms: CdaeV31.PackedVector #vtx byte
            self.regions: CdaeV31.PackedVector
            self.indices: CdaeV31.PackedVector #int
            self.tangents: CdaeV31.PackedVector #vtx vec3

            self.vertsPerFrame: int = 0
            self.flags: int = 0



    class Sequence:

        def __init__(self):
            pass


    class Material:

        def __init__(self):
            pass


    def __init__(self):

        self.smallest_visible_size: float = 0.0
        self.smallest_visible_dl: int = 0
        self.radius: float = 0.0
        self.tube_radius: float = 0.0
        self.center: Vec3F = Vec3F.create_empty()
        self.bounds: Box6F = Box6F.create_empty()

        self.nodes: list[CdaeV31.Node] = []
        self.objects: list[CdaeV31.Object] = []

        self.subShapeFirstNode: list[int] = []
        self.subShapeFirstObject: list[int] = []
        self.subShapeNumNodes: list[int] = []
        self.subShapeNumObjects: list[int] = []

        self.defaultRotations: list[Quat4F] = []
        self.defaultTranslations: list[Vec3F] = []
        self.nodeRotations: list[Quat4F] = []
        self.nodeTranslations: list[Vec3F] = []

        self.nodeUniformScales: list[float] = []
        self.nodeAlignedScales: list[Vec3F] = []
        self.nodeArbitraryScaleFactors: list[Vec3F] = []
        self.nodeArbitraryScaleRots: list[Quat4F] = []

        self.groundTranslations: list[Vec3F] = []
        self.groundRotations: list[Quat4F] = []

        self.objectStates: list[CdaeV31.ObjectState] = []
        self.triggers: list[CdaeV31.Trigger] = []
        self.details: list[CdaeV31.Detail] = []

        self.names: list[str] = []

        self.meshes: list[CdaeV31.Mesh] = []
        self.sequences: list[CdaeV31.Sequence] = []
        self.materials: list[CdaeV31.Material] = []


    def read_from_stream(self, f: BufferedReader):

        (file_version, export_version) = struct.unpack("HH", f.read(4))
        if (file_version != 31):
            raise Exception()
        
        header_size = struct.unpack("I", f.read(4))[0]
        header = MsgpackReader.from_bytes(f.read(header_size)).read_dict()

        for key in header:
            print(key)
            print(header[key])


        body = MsgpackReader.from_stream(f)

        self.smallest_visible_size = body.read_float()
        self.smallest_visible_dl = body.read_uint32()
        self.radius = body.read_float()
        self.tube_radius = body.read_float()
        self.center = body.read_vec3f()
        self.bounds = body.read_box6f()

        def read_vector():
            vec = CdaeV31.PackedVector()
            vec.element_count = body.read_uint32()
            vec.element_size = body.read_uint32()
            vec.data = body.read_bytes()
            return vec
        

        nodes = read_vector()
        objects = read_vector()

        subShapeFirstNode = read_vector()
        subShapeFirstObject = read_vector()
        subShapeNumNodes = read_vector()
        subShapeNumObjects = read_vector()

        defaultRotations = read_vector()
        defaultTranslations = read_vector()
        nodeRotations = read_vector()
        nodeTranslations = read_vector()

        nodeUniformScales = read_vector()
        nodeAlignedScales = read_vector()
        nodeArbitraryScaleFactors = read_vector()
        nodeArbitraryScaleRots = read_vector()

        groundTranslations = read_vector()
        groundRotations = read_vector()

        objectStates = read_vector()
        triggers = read_vector()
        details = read_vector()

        for chunk in nodes:
            node = CdaeV31.Node()
            (node.nameIndex, node.parentIndex, node.firstObject, node.firstChild, node.nextSibling) = struct.unpack("<5i", chunk)
            self.nodes.append(node)

        for chunk in objects:
            obj = CdaeV31.Object()
            (obj.nameIndex, obj.numMeshes, obj.startMeshIndex, obj.nodeIndex, obj.nextSibling, obj.firstDecal) = struct.unpack("<6i", chunk)
            self.objects.append(obj)


        names_count = body.read_uint32()
        print(names_count)
        for _ in range(names_count):
            name = body.read_str()
            self.names.append(name)


        meshes_count = body.read_uint32()
        for i in range(meshes_count):
            print(i)
            mesh = CdaeV31.Mesh()
            self.meshes.append(mesh)

            mesh.type = CdaeV31.MeshType(body.read_uint32())

            if (mesh.type == CdaeV31.MeshType.NULL):
                continue

            elif (mesh.type != CdaeV31.MeshType.STANDARD):
                raise Exception(mesh.type.name)

            mesh.numFrames = body.read_uint32()
            mesh.numMatFrames = body.read_uint32()
            mesh.parentMesh = body.read_uint32()
            mesh.bounds = body.read_box6f()
            mesh.center = body.read_vec3f()
            mesh.radius = body.read_float()

            mesh.verts = read_vector()
            mesh.tverts0 = read_vector()
            mesh.tverts1 = read_vector()
            mesh.colors = read_vector()
            mesh.norms = read_vector()
            mesh.encodedNorms = read_vector()
            mesh.regions = read_vector()
            mesh.indices = read_vector()
            mesh.tangents = read_vector()

            mesh.vertsPerFrame = body.read_uint32()
            mesh.flags = body.read_uint32()


    def read_from_file(self, filepath: str):

        with open(filepath, "rb") as f:
            self.read_from_stream(f)

