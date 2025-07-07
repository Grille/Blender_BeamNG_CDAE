import struct
import numpy as np

from dataclasses import dataclass
from enum import Enum
from io import BufferedReader, BufferedWriter

from .packed_vector import PackedVector
from .msgpack_reader import MsgpackReader
from .msgpack_writer import MsgpackWriter
from .numerics import *


class CdaeV31:

    @dataclass
    class Node:

        nameIndex: int = 0
        parentIndex: int = 0
        firstObject: int = 0
        firstChild: int = 0
        nextSibling: int = 0


        def unpack(self, data: bytes):
            (self.nameIndex, self.parentIndex, self.firstObject, self.firstChild, self.nextSibling) = struct.unpack("<5i", data)
        

        def pack(self):
            return struct.pack("<5i", self.nameIndex, self.parentIndex, self.firstObject, self.firstChild, self.nextSibling)


    @dataclass
    class Object:

        nameIndex: int = 0
        numMeshes: int = 0
        startMeshIndex: int = 0
        nodeIndex: int = 0
        nextSibling: int = 0
        firstDecal: int = 0


        def unpack(self, data: bytes):
            (self.nameIndex, self.numMeshes, self.startMeshIndex, self.nodeIndex, self.nextSibling, self.firstDecal) = struct.unpack("<6i", data)
        

        def pack(self):
            return struct.pack("<6i", self.nameIndex, self.numMeshes, self.startMeshIndex, self.nodeIndex, self.nextSibling, self.firstDecal)

    
    @dataclass
    class ObjectState:
        
        vis: float
        frameIndex: int
        matFrameIndex: int


    @dataclass
    class Trigger:

        state: int
        pos: float


    @dataclass
    class Detail:

        nameIndex: int = 0
        subShapeNum: int = 0
        objectDetailNum: int = 0
        size: float = 0
        averageError: float = 0
        maxError: float = 0
        polyCount: int = 0
        bbDimension: int = 0
        bbDetailLevel: int = 0
        bbEquatorSteps: int = 0
        bbPolarSteps: int = 0
        bbPolarAngle: float = 0
        bbIncludePoles: int = 0

        def unpack(self, data: bytes):
            (
                self.nameIndex, self.subShapeNum, self.objectDetailNum,
                self.size, self.averageError, self.maxError,
                self.polyCount,
                self.bbDimension, self.bbDetailLevel, self.bbEquatorSteps, self.bbPolarSteps,
                self.bbPolarAngle,
                self.bbIncludePoles
            ) = struct.unpack("<3i 3f 5i f I", data)

        def pack(self):
            return struct.pack("<3i 3f 5i f I",
                self.nameIndex, self.subShapeNum, self.objectDetailNum,
                self.size, self.averageError, self.maxError,
                self.polyCount,
                self.bbDimension, self.bbDetailLevel, self.bbEquatorSteps, self.bbPolarSteps,
                self.bbPolarAngle,
                self.bbIncludePoles
        )



    class MeshType(Enum):

        STANDARD = 0
        SKIN = 1
        DECAL = 2
        SORTED = 3
        NULL = 4



    class Mesh:

        @dataclass
        class DrawRegion:

            elements_start: int
            elements_count: int
            info: int



        def __init__(self):

            self.type = CdaeV31.MeshType.NULL

            self.numFrames: int = 0
            self.numMatFrames: int = 0
            self.parentMesh: int = 0
            self.bounds: Box6F = Box6F.create_empty()
            self.center: Vec3F = Vec3F.create_empty()
            self.radius: float = 0.0

            create_empty = PackedVector.create_empty
            self.verts = create_empty(12) #vtx vec3
            self.tverts0 = create_empty(8) #vtx vec2
            self.tverts1 = create_empty(8) #vtx vec2
            self.colors = create_empty(4) #vtx int/rgba
            self.norms = create_empty(12) #vtx vec3
            self.encoded_norms = create_empty(1) #vtx byte
            self.draw_regions = create_empty(12) #start: int, count: int, material_index: int (DrawRegion)
            self.indices = create_empty(4) #int
            self.tangents = create_empty(16) #vtx vec4

            self.vertsPerFrame: int = 0
            self.flags: int = 0



    class Sequence:

        def __init__(self):
            pass


    class Material:

        def __init__(self):
            self.name: str = ""
            self.flags: int = 0
            self.reflect: int = 0
            self.bump: int = 0
            self.detail: int = 0
            self.detailScale: float = 0
            self.reflectionAmount: float = 0


    def __init__(self):

        self.smallest_visible_size: float = 0.0
        self.smallest_visible_dl: int = 0
        self.radius: float = 0.0
        self.tube_radius: float = 0.0
        self.center: Vec3F = Vec3F.create_empty()
        self.bounds: Box6F = Box6F.create_empty()

        create_empty = PackedVector.create_empty

        self.nodes = create_empty(20) #Node
        self.objects = create_empty(24) #Object

        self.subShapeFirstNode = create_empty(4) #int
        self.subShapeFirstObject = create_empty(4) #int
        self.subShapeNumNodes = create_empty(4) #int
        self.subShapeNumObjects = create_empty(4) #int

        self.defaultRotations = create_empty(8) #quat4h
        self.defaultTranslations = create_empty(12) #vec3f
        self.nodeRotations = create_empty(8) #quat4h
        self.nodeTranslations = create_empty(12) #vec3f

        self.nodeUniformScales = create_empty(4) #float
        self.nodeAlignedScales = create_empty(12) #vec3f
        self.nodeArbitraryScaleFactors = create_empty(12) #vec3f
        self.nodeArbitraryScaleRots = create_empty(8) #quat4h

        self.groundTranslations = create_empty(12) #vec3f
        self.groundRotations = create_empty(8) #quat4h

        self.objectStates = create_empty(12) #CdaeV31.ObjectState
        self.triggers = create_empty(8) #CdaeV31.Trigger
        self.details = create_empty(52) #CdaeV31.Detail

        self.names: list[str] = []

        self.meshes: list[CdaeV31.Mesh] = []
        self.sequences: list[CdaeV31.Sequence] = []
        self.materials: list[CdaeV31.Material] = []
    

    def require_name_index(self, name: str) -> int:
        for idx, key in enumerate(self.names):
            if key == name:
                return idx
        self.names.append(name)
        return len(self.names) - 1


    def unpack_nodes(self):
        return self.nodes.unpack_list(CdaeV31.Node)


    def unpack_objects(self):
        return self.objects.unpack_list(CdaeV31.Object)
    

    def unpack_details(self):
        return self.details.unpack_list(CdaeV31.Detail)
    

    def pack_nodes(self, list):
        return self.nodes.pack_list(list)


    def pack_objects(self, list):
        return self.objects.pack_list(list)
    

    def pack_details(self, list):
        return self.details.pack_list(list)
    

    def read_from_stream(self, f: BufferedReader):

        (file_version, export_version) = struct.unpack("<HH", f.read(4))
        if (file_version != 31):
            raise Exception()
        
        header_size = struct.unpack("<I", f.read(4))[0]
        header = MsgpackReader.from_bytes(f.read(header_size)).read_dict()

        for key in header:
            print(key)
            print(header[key])


        body = MsgpackReader.from_stream(f)

        self.smallest_visible_size = body.read_float()
        self.smallest_visible_dl = body.read_int32()
        self.radius = body.read_float()
        self.tube_radius = body.read_float()
        self.center = body.read_vec3f()
        self.bounds = body.read_box6f()

        def read_vector():
            vec = PackedVector()
            vec.element_count = body.read_int32()
            vec.element_size = body.read_int32()
            vec.data = body.read_bytes()
            return vec
        

        self.nodes = read_vector()
        self.objects = read_vector()

        self.subShapeFirstNode = read_vector()
        self.subShapeFirstObject = read_vector()
        self.subShapeNumNodes = read_vector()
        self.subShapeNumObjects = read_vector()

        self.defaultRotations = read_vector()
        self.defaultTranslations = read_vector()
        self.nodeRotations = read_vector()
        self.nodeTranslations = read_vector()

        self.nodeUniformScales = read_vector()
        self.nodeAlignedScales = read_vector()
        self.nodeArbitraryScaleFactors = read_vector()
        self.nodeArbitraryScaleRots = read_vector()

        self.groundTranslations = read_vector()
        self.groundRotations = read_vector()

        self.objectStates = read_vector()
        self.triggers = read_vector()
        self.details = read_vector()


        names_count = body.read_int32()
        print(names_count)
        for _ in range(names_count):
            name = body.read_str()
            self.names.append(name)


        meshes_count = body.read_int32()
        for i in range(meshes_count):
            print(i)
            mesh = CdaeV31.Mesh()
            self.meshes.append(mesh)

            mesh.type = CdaeV31.MeshType(body.read_int32())

            if (mesh.type == CdaeV31.MeshType.NULL):
                continue

            elif (mesh.type != CdaeV31.MeshType.STANDARD):
                raise Exception(mesh.type.name)

            mesh.numFrames = body.read_int32()
            mesh.numMatFrames = body.read_int32()
            mesh.parentMesh = body.read_int32()
            mesh.bounds = body.read_box6f()
            mesh.center = body.read_vec3f()
            mesh.radius = body.read_float()

            mesh.verts = read_vector()
            mesh.tverts0 = read_vector()
            mesh.tverts1 = read_vector()
            mesh.colors = read_vector()
            mesh.norms = read_vector()
            mesh.encoded_norms = read_vector()
            mesh.draw_regions = read_vector()
            mesh.indices = read_vector()
            mesh.tangents = read_vector()

            mesh.vertsPerFrame = body.read_int32()
            mesh.flags = body.read_int32()


        seq_count = body.read_int32()
        if seq_count != 0:
            raise Exception()
        

        mat_count = body.read_int32()
        for i in range(mat_count):
            mat = CdaeV31.Material()
            self.materials.append(mat)

            mat.name = body.read_str()
            mat.flags = body.read_int32()
            mat.reflect = body.read_int32()
            mat.bump = body.read_int32()
            mat.detail = body.read_int32()
            mat.detailScale = body.read_float()
            mat.reflectionAmount = body.read_float()


    def read_from_file(self, filepath: str):

        with open(filepath, "rb") as f:
            self.read_from_stream(f)


    def get_body_bytes(self) -> bytes:

        body = MsgpackWriter()

        def write_vector(pvec: PackedVector):
            body.write_int32(pvec.element_count)
            body.write_int32(pvec.element_size)
            body.write_bytes(pvec.data)

        body.write_float(self.smallest_visible_size)
        body.write_int32(self.smallest_visible_dl)
        body.write_float(self.radius)
        body.write_float(self.tube_radius)
        body.write_vec3f(self.center)
        body.write_box6f(self.bounds)


        write_vector(self.nodes)
        write_vector(self.objects)

        write_vector(self.subShapeFirstNode)
        write_vector(self.subShapeFirstObject)
        write_vector(self.subShapeNumNodes)
        write_vector(self.subShapeNumObjects)

        write_vector(self.defaultRotations)
        write_vector(self.defaultTranslations)
        write_vector(self.nodeRotations)
        write_vector(self.nodeTranslations)

        write_vector(self.nodeUniformScales)
        write_vector(self.nodeAlignedScales)
        write_vector(self.nodeArbitraryScaleFactors)
        write_vector(self.nodeArbitraryScaleRots)

        write_vector(self.groundTranslations)
        write_vector(self.groundRotations)
        write_vector(self.objectStates)

        write_vector(self.triggers)
        write_vector(self.details)


        body.write_int32(len(self.names))
        for name in self.names:
            body.write_str(name)


        body.write_int32(len(self.meshes))
        for mesh in self.meshes:

            body.write_int32(mesh.type.value)

            if mesh.type == CdaeV31.MeshType.NULL:
                continue

            body.write_int32(mesh.numFrames)
            body.write_int32(mesh.numMatFrames)
            body.write_int32(mesh.parentMesh)
            body.write_box6f(mesh.bounds)
            body.write_vec3f(mesh.center)
            body.write_float(mesh.radius)

            write_vector(mesh.verts)
            write_vector(mesh.tverts0)
            write_vector(mesh.tverts1)
            write_vector(mesh.colors)
            write_vector(mesh.norms)
            write_vector(mesh.encoded_norms)
            write_vector(mesh.draw_regions)
            write_vector(mesh.indices)
            write_vector(mesh.tangents)

            body.write_int32(mesh.vertsPerFrame)
            body.write_int32(mesh.flags)


        body.write_int32(len(self.sequences))
        for obj in self.sequences:
            pass


        body.write_int32(len(self.materials))
        for obj in self.materials:
            body.write_str(obj.name)
            body.write_int32(obj.flags)
            body.write_int32(obj.reflect)
            body.write_int32(obj.bump)
            body.write_int32(obj.detail)
            body.write_float(obj.detailScale)
            body.write_float(obj.reflectionAmount)

        return body.to_bytes()
    

    def get_object_names(self) -> list[str]:
        list = []
        for obj in self.unpack_objects():
            list.append(self.names[obj.nameIndex])
        return list

    
    def write_to_stream(self, f: BufferedWriter):

        body_bytes = self.get_body_bytes()

        head = MsgpackWriter()
        head_dict = {
            "info": "Welcome! This is a binary file :D Please read the docs at https://go.beamng.com/shapeMessagepackFileformat",
            "compression": False,
            "bodysize": len(body_bytes),
            "objectNames": self.get_object_names(),
        }
        head.write_dict(head_dict)
        head_bytes = head.to_bytes()

        f.write(struct.pack("<HH", 31, 0))
        f.write(struct.pack("<I", len(head_bytes)))
        f.write(head_bytes)
        f.write(body_bytes)


    def write_to_file(self, filepath: str):

        with open(filepath, 'wb') as f:
            self.write_to_stream(f)