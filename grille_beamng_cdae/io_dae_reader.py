import struct
import numpy as np
import zstandard as zstd
import xml.etree.cElementTree as ET

from dataclasses import dataclass
from enum import Enum
from io import BufferedReader
from numpy.typing import NDArray

from .io_dae import *
from .cdae_v31 import CdaeV31
from .numerics import *


def parse_array(xml: ET.Element, dtype=np.float32) -> NDArray:
    return np.fromstring(xml.text, dtype=dtype, sep=" ")


def parse_input(xml: ET.Element) -> Geometry.Triangles.Input:
    return Geometry.Triangles.Input(Semantic(xml.get("semantic")), xml.get("source"), xml.get("offset", 0), xml.get("set", 0))


def parse_triangle(xml: ET.Element) -> Geometry.Triangles:
    result = Geometry.Triangles()

    result.indices = parse_array(xml.find(DaeTag.p), np.int32)
    inputlist = xml.findall(DaeTag.param)
    for input in inputlist:
        result.inputs.append(parse_input(input))

    return result


def parse_geometry(xml: ET.Element) -> Geometry:
    result = Geometry()
    mesh = xml.find(DaeTag.mesh)

    srclist = mesh.findall(DaeTag.source)
    for src in srclist:
        array = parse_array(src.find(DaeTag.float_array))
        result.sources[src.get("id")] = array

    trilist0 = mesh.findall(DaeTag.triangles)
    for tri in trilist0:
        result.triangles.append(parse_triangle(tri))

    trilist1 = mesh.findall(DaeTag.polylist)
    for tri in trilist1:
        result.triangles.append(parse_triangle(tri))

    return result


def parse_node(xml: ET.Element) -> Node:
    res = Node()
    nodelist = xml.findall(DaeTag.node)
    for node in nodelist:
        res.children.append(parse_node(node))
    return res


def parse_collada(xml: ET.Element) -> Collada:
    dae = Collada()
    
    matlib = xml.find(DaeTag.library_materials)
    matlist = matlib.findall(DaeTag.material)
    for mat in matlist:
        dae.materials.append(Material(mat.get("id"), mat.get("name")))

    geolib = xml.find(DaeTag.library_geometries)
    geolist = geolib.findall(DaeTag.geometry)
    for geo in geolist:
        dae.geometries.append(parse_geometry(geo))

    scnlib = xml.find(DaeTag.library_visual_scenes)
    scn = scnlib.find(DaeTag.visual_scene)
    nodelist = scn.findall(DaeTag.node)
    for node in nodelist:
        dae.nodes.append(parse_node(node))
    
    return dae


def convert_material(daemat: Material) -> CdaeV31.Material:
    mat = CdaeV31.Material()
    mat.name = daemat.name

    return mat


def convert_geometry(geo: Geometry) -> CdaeV31.Mesh:
    mesh = CdaeV31.Mesh()

    return mesh


def convert(dae: Collada):
    cdae = CdaeV31()

    for mat in dae.materials:
        cdae.materials.append(convert_material(mat))

    for geo in dae.geometries:
        cdae.meshes.append(convert_geometry(geo))

    cdae.unpack_tree()

    return cdae



class DaeReader:

    @staticmethod
    def read_from_stream(stream: BufferedReader):
        tree = ET.parse(stream)
        dae = parse_collada(tree.find(DaeTag.COLLADA))
        return convert(dae)


    @staticmethod
    def read_from_file(filepath: str) -> CdaeV31:

        with open(filepath, "rb") as f:
            return DaeReader.read_from_stream(f)