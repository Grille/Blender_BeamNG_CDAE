import struct
import numpy as np

from dataclasses import dataclass, asdict
from enum import Enum
from io import BufferedReader, BufferedWriter

from .packed_vector import PackedVector
from .msgpack_reader import MsgpackReader
from .msgpack_writer import MsgpackWriter
from .numerics import *


class CdaeV31:

    @dataclass
    class Node:

        nameIndex: int = -1
        parentIndex: int = -1
        firstObject: int = -1
        firstChild: int = -1
        nextSibling: int = -1


        def unpack(self, data: bytes):
            (self.nameIndex, self.parentIndex, self.firstObject, self.firstChild, self.nextSibling) = struct.unpack("<5i", data)
        

        def pack(self):
            return struct.pack("<5i", self.nameIndex, self.parentIndex, self.firstObject, self.firstChild, self.nextSibling)



    @dataclass
    class Object:

        nameIndex: int = -1
        numMeshes: int = 0
        startMeshIndex: int = -1
        nodeIndex: int = -1
        nextSibling: int = -1
        firstDecal: int = -1


        def unpack(self, data: bytes):
            (self.nameIndex, self.numMeshes, self.startMeshIndex, self.nodeIndex, self.nextSibling, self.firstDecal) = struct.unpack("<6i", data)
        

        def pack(self):
            return struct.pack("<6i", self.nameIndex, self.numMeshes, self.startMeshIndex, self.nodeIndex, self.nextSibling, self.firstDecal)

    

    class Tree:

        def __init__(self, cdae: 'CdaeV31', nodes: 'list[CdaeV31.Node]', objects: 'list[CdaeV31.Object]'):

            self.cdae = cdae
            self.nodes = nodes
            self.objects = objects


        def enumerate_root(self):
            for node_index, node in enumerate(self.nodes):
                if node.parentIndex == -1:
                    yield (node_index, node)


        def enumerate_child_nodes(self, node_index: int):
            node_index = self.nodes[node_index].firstChild
            while node_index != -1:
                node = self.nodes[node_index]
                yield (node_index, node)
                node_index = node.nextSibling


        def enumerate_child_objects(self, node_index: int):
            obj_index = self.nodes[node_index].firstObject
            while obj_index != -1:
                obj = self.objects[obj_index]
                yield (obj_index, obj)
                obj_index = obj.nextSibling


        def enumerate_mesh_indexes(self, obj_index: int):
            obj = self.objects[obj_index]
            for mesh_index in range(obj.startMeshIndex, obj.startMeshIndex + obj.numMeshes):
                yield mesh_index


        def enumerate_meshes(self, obj_index: int):
            for mesh_index in self.enumerate_mesh_indexes(obj_index):
                yield (mesh_index, self.cdae.meshes[mesh_index])


        def create_node(self):
            node_index = len(self.nodes)
            node = CdaeV31.Node()
            self.nodes.append(node)
            return (node_index, node)


        def create_object(self):
            obj_index = len(self.objects)
            obj = CdaeV31.Object()
            self.objects.append(obj)
            return (obj_index, obj)
        

        def _set_last_sibling(list: 'list[CdaeV31.Node|CdaeV31.Object]', current_index: int, value: int):
            next_index = list[current_index].nextSibling
            if next_index == -1:
                list[current_index].nextSibling = value
            else:
                CdaeV31.Tree._set_last_sibling(list, next_index, value)


        def link_node(self, parent_index: int, node_index: int):
            if (self.nodes[node_index].parentIndex) != -1:
                raise ValueError("Already parented")
            
            if parent_index == -1:
                return
            
            self.nodes[node_index].parentIndex = parent_index

            first = self.nodes[parent_index].firstChild
            if first == -1:
                self.nodes[parent_index].firstChild = node_index
                return
            
            CdaeV31.Tree._set_last_sibling(self.nodes, first, node_index)


        def link_object(self, parent_index: int, obj_index: int):
            if (self.objects[obj_index].nodeIndex) != -1:
                raise ValueError("Already parented")
            
            if parent_index == -1:
                return
            
            self.objects[obj_index].nodeIndex = parent_index

            first = self.nodes[parent_index].firstObject
            if first == -1:
                self.nodes[parent_index].firstObject = obj_index
                return
            
            CdaeV31.Tree._set_last_sibling(self.objects, first, obj_index)



    @dataclass
    class ObjectState:
        
        vis: float = 1.0
        frameIndex: int = 0
        matFrameIndex: int = 0


        def unpack(self, data: bytes):
            self.vis, self.frameIndex, self.matFrameIndex = struct.unpack("<fii", data)

        def pack(self):
            return struct.pack("<fii", self.vis, self.frameIndex, self.matFrameIndex)



    @dataclass
    class Trigger:

        state: int = 0
        pos: float = 0.0


        def unpack(self, data: bytes):
            self.state, self.pos = struct.unpack("<if", data)

        def pack(self):
            return struct.pack("<if", self.state, self.pos)



    @dataclass
    class SubShape:

        firstNode: int = 0
        firstObject: int = 0
        numNodes: int = 0
        numObjects: int = 0



    @dataclass
    class Detail:

        nameIndex: int = 0
        subShapeNum: int = 0
        objectDetailNum: int = 0
        size: float = 0
        averageError: float = -1.0
        maxError: float = -1.0
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

        def asdict(self): return asdict(self)



    class MeshType(int, Enum):

        STANDARD = 0
        SKIN = 1
        DECAL = 2
        SORTED = 3
        NULL = 4



    class Mesh:

        @dataclass
        class DrawRegion:

            class InfoMask(int, Enum):
                TYPE_MASK = 0xC0000000
                INDEXED = 0x20000000
                NO_MATERIAL = 0x10000000
                MATERIAL_MASK = 0x0FFFFFFF


            class DrawType(int, Enum):
                Triangles = 0x00000000
                Strip = 0x40000000
                Fan = 0x80000000


            @dataclass
            class DrawInfo:
                type: 'CdaeV31.Mesh.DrawRegion.DrawType'
                is_indexed: bool
                has_no_mat: bool


            elements_start: int = 0
            elements_count: int = 0
            raw_info: int = 0
            

            @property
            def material(self) -> int:
                return self.raw_info & CdaeV31.Mesh.DrawRegion.InfoMask.MATERIAL_MASK
            
            @material.setter
            def material(self, value: int):
                self.raw_info = (self.raw_info & ~CdaeV31.Mesh.DrawRegion.InfoMask.MATERIAL_MASK) | (value & CdaeV31.Mesh.DrawRegion.InfoMask.MATERIAL_MASK)

            
            @property
            def info(self):
                draw_type = CdaeV31.Mesh.DrawRegion.DrawType(self.raw_info & CdaeV31.Mesh.DrawRegion.InfoMask.TYPE_MASK)
                is_indexed = bool(self.raw_info & CdaeV31.Mesh.DrawRegion.InfoMask.INDEXED)
                has_no_mat = bool(self.raw_info & CdaeV31.Mesh.DrawRegion.InfoMask.NO_MATERIAL)
                return CdaeV31.Mesh.DrawRegion.DrawInfo(draw_type, is_indexed, has_no_mat)


            def get_polygon_range(self) -> range:
                start = self.elements_start // 3
                count = self.elements_count // 3
                stop = start + count
                return range(start, stop)


            def unpack(self, data: bytes):
                self.elements_start, self.elements_count, self.raw_info = struct.unpack("<iii", data)

            def pack(self):
                return struct.pack("<iii", self.elements_start, self.elements_count, self.raw_info)



        def __init__(self):

            self.type = CdaeV31.MeshType.NULL

            self.numFrames: int = 0
            self.numMatFrames: int = 0
            self.parentMesh: int = -1
            self.bounds: Box6F = Box6F()
            self.center: Vec3F = Vec3F()
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


        def unpack_regions(self):
            return self.draw_regions.unpack_list(CdaeV31.Mesh.DrawRegion)


        def get_vec4f_colors(self):
            byte_array = self.colors.to_numpy_array(np.ubyte)
            float_array = byte_array.astype(np.float32) / 255.0
            return float_array
        

        def data_equals(self, other: 'CdaeV31.Mesh') -> bool:
            pass



    class Sequence:

        def __init__(self):
            self.nameIndex: int = 0
            self.flags: int = 0
            self.numKeyframes: int = 0
            self.duration: float = 0
            self.priority: int = 0
            self.firstGroundFrame: int = 0
            self.numGroundFrames: int = 0
            self.baseRotation: int = 0
            self.baseTranslation: int = 0
            self.baseScale: int = 0
            self.baseObjectState: int = 0
            self.baseDecalState: int = 0
            self.firstTrigger: int = 0
            self.numTriggers: int = 0
            self.toolBegin: float = 0

            self.rotationMatters: list[bool] = []
            self.translationMatters: list[bool] = []
            self.scaleMatters: list[bool] = []
            self.visMatters: list[bool] = []
            self.frameMatters: list[bool] = []
            self.matFrameMatters: list[bool] = []



    class Material:

        def __init__(self):
            self.name: str = ""
            self.flags: int = 3
            self.reflect: int = 0
            self.bump: int = 0
            self.detail: int = 0
            self.detailScale: float = 1.0
            self.reflectionAmount: float = 1.0


    def __init__(self):
        self.smallest_visible_size: float = 2.0
        self.smallest_visible_dl: int = 0
        self.radius: float = 5.0
        self.tube_radius: float = 5.0
        self.center: Vec3F = Vec3F()
        self.bounds: Box6F = Box6F(-2,-2,-2, 2, 2, 2)

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


    def get_name_index(self, name: str) -> int:
        for idx, key in enumerate(self.names):
            if key == name:
                return idx
        self.names.append(name)
        return len(self.names) - 1


    def unpack_nodes(self):
        return self.nodes.unpack_list(CdaeV31.Node)


    def unpack_objects(self):
        return self.objects.unpack_list(CdaeV31.Object)
    

    def unpack_tree(self):
        return CdaeV31.Tree(self, self.unpack_nodes(), self.unpack_objects())
    

    def unpack_subshapes(self):
        fn = self.subShapeFirstNode.to_numpy_array(np.uint32)
        nn = self.subShapeNumNodes.to_numpy_array(np.uint32)
        fo = self.subShapeFirstObject.to_numpy_array(np.uint32)
        no = self.subShapeNumObjects.to_numpy_array(np.uint32)

        count = fn.size
        assert all(arr.size == count for arr in (nn, fo, no)), "Subshape buffers must have the same length"

        shapes: list[CdaeV31.SubShape] = []
        for firstNode, numNodes, firstObject, numObjects in zip(fn, nn, fo, no):
            shape = CdaeV31.SubShape(
                firstNode=int(firstNode),
                numNodes=int(numNodes),
                firstObject=int(firstObject),
                numObjects=int(numObjects)
            )
            shapes.append(shape)
        return shapes
    

    def unpack_details(self):
        return self.details.unpack_list(CdaeV31.Detail)
    

    def unpack_triggers(self):
        return self.triggers.unpack_list(CdaeV31.Trigger)
    

    def unpack_states(self):
        return self.objectStates.unpack_list(CdaeV31.ObjectState)
    

    def pack_nodes(self, list):
        return self.nodes.pack_list(list)


    def pack_objects(self, list):
        return self.objects.pack_list(list)
    

    def pack_tree(self, tree: 'CdaeV31.Tree'):
        self.pack_nodes(tree.nodes)
        self.pack_objects(tree.objects)
    

    def pack_subshapes(self, subshapes: 'list[CdaeV31.SubShape]'):
        count = len(subshapes)

        fn = np.empty(count, dtype=np.uint32)
        nn = np.empty(count, dtype=np.uint32)
        fo = np.empty(count, dtype=np.uint32)
        no = np.empty(count, dtype=np.uint32)

        for i, s in enumerate(subshapes):
            fn[i] = s.firstNode
            nn[i] = s.numNodes
            fo[i] = s.firstObject
            no[i] = s.numObjects

        self.subShapeFirstNode.set_numpy_array(fn)
        self.subShapeNumNodes.set_numpy_array(nn)
        self.subShapeFirstObject.set_numpy_array(fo)
        self.subShapeNumObjects.set_numpy_array(no)
    

    def pack_details(self, list):
        return self.details.pack_list(list)
    

    def pack_triggers(self, list):
        return self.triggers.pack_list(list)
    

    def pack_states(self, list):
        return self.objectStates.pack_list(list)
    

    def print_debug(self):
        print("---------------------")
        print("tree-count")
        print(self.nodes.element_count)
        print(self.objects.element_count)
        print(len(self.meshes))

        print("blobs")
        print("- default")
        print(self.defaultRotations.element_count)
        print(self.defaultTranslations.element_count)
        print("- node")
        print(self.nodeRotations.element_count)
        print(self.nodeTranslations.element_count)
        print("- scale")
        print(self.nodeUniformScales.element_count)
        print(self.nodeAlignedScales.element_count)
        print(self.nodeArbitraryScaleFactors.element_count)
        print(self.nodeArbitraryScaleRots.element_count)
        print("- ground")
        print(self.groundRotations.element_count)
        print(self.groundTranslations.element_count)