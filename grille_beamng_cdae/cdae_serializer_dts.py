import struct
import numpy as np
import zstandard as zstd

from dataclasses import dataclass
from enum import Enum
from io import BufferedReader, BufferedWriter, BytesIO

from .cdae_v31 import CdaeV31
from .packed_vector import PackedVector
from .msgpack_reader import MsgpackReader
from .msgpack_writer import MsgpackWriter
from .numerics import *


class CdaeDtsBuffers:
        
    def __init__(self):
        self.guard_index = 0
        self.b8 = BytesIO()
        self.b16 = BytesIO()
        self.b32 = BytesIO()


    def write_u8(self, value: int):
        self.b8.write(struct.pack("<B", value))


    def write_s8(self, value: int):
        self.b8.write(struct.pack("<b", value))


    def write_u16(self, value: int):
        self.b16.write(struct.pack("<H", value))


    def write_s16(self, value: int):
        self.b16.write(struct.pack("<h", value))


    def write_u32(self, value: int):
        self.b32.write(struct.pack("<I", value))
        

    def write_s32(self, value: int):
        self.b32.write(struct.pack("<i", value))
        

    def write_f32(self, value: float):
        self.b32.write(struct.pack("<f", value))


    def write_vec3(self, value: Vec3F):
        self.write_f32(value.x)
        self.write_f32(value.y)
        self.write_f32(value.z)


    def write_str(self, value: str):
        data = value.encode("utf-8")
        self.b8.write(data)
        self.b8.write(b"\x00")  # null terminator


    def write_box6(self, value: Box6F):
        self.write_vec3(value.min)
        self.write_vec3(value.max)


    def write_guard(self):
        self.write_s8(self.guard_index)
        self.write_s16(self.guard_index)
        self.write_s32(self.guard_index)
        self.guard_index += 1


    def write_mesh(self, mesh: CdaeV31.Mesh):
        
        self.write_u32(mesh.type)
        self.write_guard()
        if mesh.type == CdaeV31.MeshType.NULL:
            return
        
        if mesh.type != CdaeV31.MeshType.STANDARD:
            raise Exception()
        
        self.write_s32(mesh.numFrames)
        self.write_s32(mesh.numMatFrames)
        self.write_s32(mesh.parentMesh)
        self.write_box6(mesh.bounds)
        self.write_vec3(mesh.center)
        self.write_f32(mesh.radius)

        self.write_s32(mesh.verts.element_count)
        self.b32.write(mesh.verts.data)
        self.write_s32(mesh.tverts0.element_count)
        self.b32.write(mesh.tverts0.data)
        self.write_s32(mesh.tverts1.element_count)
        self.b32.write(mesh.tverts1.data)
        self.write_s32(mesh.colors.element_count)
        self.b32.write(mesh.colors.data)
        self.b32.write(mesh.norms.data)
        self.b8.write(mesh.encoded_norms.data)
        self.write_s32(mesh.draw_regions.element_count)
        self.b32.write(mesh.draw_regions.data)
        self.write_s32(mesh.indices.element_count)
        self.b32.write(mesh.indices.data)
        self.write_s32(0) #numMergeIndices
        #mergeIndices
        self.write_s32(mesh.vertsPerFrame)
        self.write_u32(mesh.flags)
        self.write_guard()


    def write_data_to_buffers(self, cdae: CdaeV31):
        
        self.write_s32(cdae.nodes.element_count)
        self.write_s32(cdae.objects.element_count)
        self.write_s32(0) #numDecals
        self.write_s32(cdae.subShapeFirstNode.element_count)
        self.write_s32(0) #numIFLs
        self.write_s32(cdae.nodeRotations.element_count)
        self.write_s32(cdae.nodeTranslations.element_count)
        self.write_s32(cdae.nodeUniformScales.element_count)
        self.write_s32(cdae.nodeAlignedScales.element_count)
        self.write_s32(0) #numNodeArbScales
        self.write_s32(0) #numGroundFrames
        self.write_s32(cdae.objectStates.element_count)
        self.write_s32(0) #numDecalStates
        self.write_s32(cdae.triggers.element_count)
        self.write_s32(cdae.details.element_count)
        self.write_s32(len(cdae.meshes))
        self.write_s32(len(cdae.names))
        self.write_f32(cdae.smallest_visible_size)
        self.write_s32(cdae.smallest_visible_dl)
        self.write_guard()

        self.write_f32(cdae.radius)
        self.write_f32(cdae.tube_radius)
        self.write_vec3(cdae.center)
        self.write_box6(cdae.bounds)
        self.write_guard()

        self.b32.write(cdae.nodes.data)
        self.write_guard()

        self.b32.write(cdae.objects.data)
        self.write_guard()

        #decals
        self.write_guard()

        #iflMaterials
        self.write_guard()

        self.b32.write(cdae.subShapeFirstNode.data)
        self.b32.write(cdae.subShapeFirstObject.data)
        self.b32.write(bytearray(cdae.subShapeFirstNode.element_count*4)) #subShapeFirstDecal
        self.b32.write(bytearray(cdae.subShapeFirstNode.element_count*4)) #subShapeFirstTranslucentObject
        self.write_guard()

        self.b32.write(cdae.defaultRotations.data)
        self.b32.write(cdae.defaultTranslations.data)
        self.b32.write(cdae.nodeRotations.data)
        self.b32.write(cdae.nodeTranslations.data)
        self.write_guard()

        self.b32.write(cdae.nodeUniformScales.data)
        self.b32.write(cdae.nodeAlignedScales.data)
        #nodeArbScaleFactors
        #nodeArbScaleRots
        self.write_guard()

        self.b32.write(cdae.groundTranslations.data)
        self.b32.write(cdae.groundRotations.data)
        self.write_guard()

        self.b32.write(cdae.objectStates.data)
        self.write_guard()

        self.b32.write(cdae.triggers.data)
        self.write_guard()

        self.b32.write(cdae.details.data)
        self.write_guard()

        for mesh in cdae.meshes:
            self.write_mesh(mesh)
        self.write_guard()

        for name in cdae.names:
            self.write_str(name)
        self.write_guard()

        self.write_f32(0) #alphaIn
        self.write_f32(0) #alphaOut



class CdaeDtsSerializer:

    @staticmethod
    def write_to_stream(cdae: CdaeV31, f: BufferedWriter):

        def write_s8(value: int): f.write(struct.pack("<b", value))
        def write_s16(value: int): f.write(struct.pack("<h", value))
        def write_s32(value: int): f.write(struct.pack("<i", value))
        def write_u32(value: int): f.write(struct.pack("<I", value))
        def write_f32(value: float): f.write(struct.pack("<f", value))

        self = CdaeDtsBuffers()
        self.write_data_to_buffers(cdae)
        buffer32 = self.b32.getvalue()
        buffer16 = self.b16.getvalue()
        buffer8 = self.b8.getvalue()

        write_s16(26)
        write_s16(0)
        write_s32(len(buffer32)+len(buffer16)+len(buffer8))
        write_s32(len(buffer32))
        write_s32(len(buffer32)+len(buffer16))
        f.write(buffer32)
        f.write(buffer16)
        f.write(buffer8)
        write_s32(len(cdae.sequences))
        for seq in cdae.sequences:
            write_s32(seq.nameIndex)
            write_u32(seq.flags)
            #TODO:
        write_s8(1) #matStreamType binary
        write_s32(len(cdae.materials))
        for mat in cdae.materials:
            write_s32(len(mat.name))
            f.write(mat.name.encode("utf-8"))
            f.write(b"\x00")  # null terminator
        for _ in cdae.materials:
            f.write(bytearray(7*4))


    @staticmethod
    def write_to_file(cdae: CdaeV31, filepath: str):

        with open(filepath, 'wb') as f:
            CdaeDtsSerializer.write_to_stream(cdae, f)