import struct
import numpy as np
import zstandard as zstd

from dataclasses import dataclass
from enum import Enum
from io import BufferedReader, BufferedWriter

from .cdae_v31 import CdaeV31
from .packed_vector import PackedVector
from .msgpack_reader import MsgpackReader
from .msgpack_writer import MsgpackWriter
from .numerics import *



def read_from_stream(f: BufferedReader) -> CdaeV31:

    cdae = CdaeV31()

    (file_version, export_version) = struct.unpack("<HH", f.read(4))
    if (file_version != 31):
        raise Exception()
    
    header_size = struct.unpack("<I", f.read(4))[0]
    header = MsgpackReader.from_bytes(f.read(header_size)).read_dict()

    for key in header:
        print(key)
        print(header[key])

    is_compressed = header.get('compression', False)

    body_data = f.read()

    if is_compressed:
        dctx = zstd.ZstdDecompressor()
        body_data = dctx.decompress(body_data)

    body = MsgpackReader.from_bytes(body_data)

    cdae.smallest_visible_size = body.read_float()
    cdae.smallest_visible_dl = body.read_int32()
    cdae.radius = body.read_float()
    cdae.tube_radius = body.read_float()
    cdae.center = body.read_vec3f()
    cdae.bounds = body.read_box6f()

    def read_vector():
        vec = PackedVector()
        vec.element_count = body.read_int32()
        vec.element_size = body.read_int32()
        vec.data = body.read_bytes()
        return vec
    

    cdae.nodes = read_vector()
    cdae.objects = read_vector()

    cdae.subShapeFirstNode = read_vector()
    cdae.subShapeFirstObject = read_vector()
    cdae.subShapeNumNodes = read_vector()
    cdae.subShapeNumObjects = read_vector()

    cdae.defaultRotations = read_vector()
    cdae.defaultTranslations = read_vector()
    cdae.nodeRotations = read_vector()
    cdae.nodeTranslations = read_vector()

    cdae.nodeUniformScales = read_vector()
    cdae.nodeAlignedScales = read_vector()
    cdae.nodeArbitraryScaleFactors = read_vector()
    cdae.nodeArbitraryScaleRots = read_vector()

    cdae.groundTranslations = read_vector()
    cdae.groundRotations = read_vector()

    cdae.objectStates = read_vector()
    cdae.triggers = read_vector()
    cdae.details = read_vector()


    names_count = body.read_int32()
    print(names_count)
    for _ in range(names_count):
        name = body.read_str()
        cdae.names.append(name)


    meshes_count = body.read_int32()
    for i in range(meshes_count):
        print(i)
        mesh = CdaeV31.Mesh()
        cdae.meshes.append(mesh)

        mesh.type = CdaeV31.MeshType(body.read_int32())

        if (mesh.type == CdaeV31.MeshType.NULL):
            continue

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

        if (mesh.type == CdaeV31.MeshType.STANDARD):
            continue

        elif (mesh.type == CdaeV31.MeshType.SKIN):
            raise Exception()
        
        else:
            raise Exception()


    seq_count = body.read_int32()
    if seq_count != 0:
        seq = CdaeV31.Sequence()
        cdae.sequences.append(seq)

        seq.nameIndex = body.read_int32()
        seq.flags = body.read_int32()
        seq.numKeyframes = body.read_int32()
        seq.duration = body.read_float()
        seq.priority = body.read_int32()
        seq.firstGroundFrame = body.read_int32()
        seq.numGroundFrames = body.read_int32()
        seq.baseRotation = body.read_int32()
        seq.baseTranslation = body.read_int32()
        seq.baseScale = body.read_int32()
        seq.baseObjectState = body.read_int32()
        seq.baseDecalState = body.read_int32()
        seq.firstTrigger = body.read_int32()
        seq.numTriggers = body.read_int32()
        seq.toolBegin = body.read_float()

        seq.rotationMatters = body.read_integerset()
        seq.translationMatters = body.read_integerset()
        seq.scaleMatters = body.read_integerset()
        seq.visMatters = body.read_integerset()  
        seq.frameMatters = body.read_integerset()
        seq.matFrameMatters = body.read_integerset()
    

    mat_count = body.read_int32()
    for i in range(mat_count):
        mat = CdaeV31.Material()
        cdae.materials.append(mat)

        mat.name = body.read_str()
        mat.flags = body.read_int32()
        mat.reflect = body.read_int32()
        mat.bump = body.read_int32()
        mat.detail = body.read_int32()
        mat.detailScale = body.read_float()
        mat.reflectionAmount = body.read_float()

    return cdae


def read_from_file(filepath: str) -> CdaeV31:

    with open(filepath, "rb") as f:
        return read_from_stream(f)



def get_body_bytes(cdae: CdaeV31) -> bytes:

    body = MsgpackWriter()

    def write_vector(pvec: PackedVector):
        body.write_int32(pvec.element_count)
        body.write_int32(pvec.element_size)
        body.write_bytes(pvec.data)

    body.write_float(cdae.smallest_visible_size)
    body.write_int32(cdae.smallest_visible_dl)
    body.write_float(cdae.radius)
    body.write_float(cdae.tube_radius)
    body.write_vec3f(cdae.center)
    body.write_box6f(cdae.bounds)


    write_vector(cdae.nodes)
    write_vector(cdae.objects)

    write_vector(cdae.subShapeFirstNode)
    write_vector(cdae.subShapeFirstObject)
    write_vector(cdae.subShapeNumNodes)
    write_vector(cdae.subShapeNumObjects)

    write_vector(cdae.defaultRotations)
    write_vector(cdae.defaultTranslations)
    write_vector(cdae.nodeRotations)
    write_vector(cdae.nodeTranslations)

    write_vector(cdae.nodeUniformScales)
    write_vector(cdae.nodeAlignedScales)
    write_vector(cdae.nodeArbitraryScaleFactors)
    write_vector(cdae.nodeArbitraryScaleRots)

    write_vector(cdae.groundTranslations)
    write_vector(cdae.groundRotations)
    write_vector(cdae.objectStates)

    write_vector(cdae.triggers)
    write_vector(cdae.details)


    body.write_int32(len(cdae.names))
    for name in cdae.names:
        body.write_str(name)


    body.write_int32(len(cdae.meshes))
    for mesh in cdae.meshes:

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


    body.write_int32(len(cdae.sequences))
    for obj in cdae.sequences:
        raise Exception()


    body.write_int32(len(cdae.materials))
    for obj in cdae.materials:
        body.write_str(obj.name)
        body.write_int32(obj.flags)
        body.write_int32(obj.reflect)
        body.write_int32(obj.bump)
        body.write_int32(obj.detail)
        body.write_float(obj.detailScale)
        body.write_float(obj.reflectionAmount)

    return body.to_bytes()


def get_object_names(cdae: CdaeV31) -> list[str]:
    list = []
    for obj in cdae.unpack_objects():
        list.append(cdae.names[obj.nameIndex])
    return list


def write_to_stream(cdae: CdaeV31, f: BufferedWriter):

    body_bytes = get_body_bytes(cdae)

    head = MsgpackWriter()
    head_dict = {
        "info": "Welcome! This is a binary file :D Please read the docs at https://go.beamng.com/shapeMessagepackFileformat",
        "compression": False,
        "bodysize": len(body_bytes),
        "objectNames": get_object_names(cdae),
    }
    head.write_dict(head_dict)
    head_bytes = head.to_bytes()

    f.write(struct.pack("<HH", 31, 0))
    f.write(struct.pack("<I", len(head_bytes)))
    f.write(head_bytes)
    f.write(body_bytes)


def write_to_file(cdae: CdaeV31, filepath: str):

    with open(filepath, 'wb') as f:
        write_to_stream(cdae, f)