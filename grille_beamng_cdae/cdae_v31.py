import struct
import numpy as np

from enum import Enum
from io import BufferedReader, BufferedWriter

from .packed_vector import PackedVector
from .msgpack_reader import MsgpackReader
from .msgpack_writer import MsgpackWriter
from .numerics import *


class CdaeV31:

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

            create_empty = PackedVector.create_empty
            self.verts = create_empty() #vtx vec3
            self.tverts0 = create_empty() #vtx vec2
            self.tverts1 = create_empty() #vtx vec2
            self.colors = create_empty() #vtx int/rgba
            self.norms = create_empty() #vtx vec3
            self.encodedNorms = create_empty() #vtx byte
            self.regions = create_empty()
            self.indices = create_empty() #int
            self.tangents = create_empty() #vtx vec3

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

        create_empty = PackedVector.create_empty

        self.nodes = create_empty() #Node
        self.objects = create_empty() #Object

        self.subShapeFirstNode = create_empty() #int
        self.subShapeFirstObject = create_empty() #int
        self.subShapeNumNodes = create_empty() #int
        self.subShapeNumObjects = create_empty() #int

        self.defaultRotations = create_empty() #quat4h
        self.defaultTranslations = create_empty() #vec3f
        self.nodeRotations = create_empty() #quat4h
        self.nodeTranslations = create_empty() #quat4h

        self.nodeUniformScales = create_empty() #float
        self.nodeAlignedScales = create_empty() #vec3f
        self.nodeArbitraryScaleFactors = create_empty() #vec3f
        self.nodeArbitraryScaleRots = create_empty() #quat4h

        self.groundTranslations = create_empty() #vec3f
        self.groundRotations = create_empty() #quat4h

        self.objectStates = create_empty() #CdaeV31.ObjectState
        self.triggers = create_empty() #CdaeV31.Trigger
        self.details = create_empty() #CdaeV31.Detail

        self.names: list[str] = []

        self.meshes: list[CdaeV31.Mesh] = []
        self.sequences: list[CdaeV31.Sequence] = []
        self.materials: list[CdaeV31.Material] = []


    def unpack_nodes(self):
        unpacked: list[CdaeV31.Node] = []
        for chunk in self.nodes:
            node = CdaeV31.Node()
            (node.nameIndex, node.parentIndex, node.firstObject, node.firstChild, node.nextSibling) = struct.unpack("<5i", chunk)
            unpacked.append(node)
        return unpacked


    def unpack_objects(self):
        unpacked: list[CdaeV31.Object] = []
        for chunk in self.objects:
            obj = CdaeV31.Object()
            (obj.nameIndex, obj.numMeshes, obj.startMeshIndex, obj.nodeIndex, obj.nextSibling, obj.firstDecal) = struct.unpack("<6i", chunk)
            unpacked.append(obj)
        return unpacked


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
            mesh.encodedNorms = read_vector()
            mesh.regions = read_vector()
            mesh.indices = read_vector()
            mesh.tangents = read_vector()

            mesh.vertsPerFrame = body.read_int32()
            mesh.flags = body.read_int32()


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
            write_vector(mesh.encodedNorms)
            write_vector(mesh.regions)
            write_vector(mesh.indices)
            write_vector(mesh.tangents)

            body.write_int32(mesh.vertsPerFrame)
            body.write_int32(mesh.flags)

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
            "compression": False,
            "bodysize": len(body_bytes),
            "objectNames": self.get_object_names(),
        }
        head.write_dict(head_dict)
        head_bytes = head.to_bytes()

        f.write(struct.pack("HH", 31, 0))
        f.write(struct.pack("I", len(head_bytes)))
        f.write(head_bytes)
        f.write(body_bytes)


    def write_to_file(self, filepath: str):

        with open(filepath, 'wb') as f:
            self.write_to_stream(f)