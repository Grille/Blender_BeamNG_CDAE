import struct
import numpy as np
import zstandard as zstd
import xml.etree.cElementTree as ET

from dataclasses import dataclass
from enum import Enum
from io import BufferedReader
from numpy.typing import NDArray

from .dae import *
from ..packed_vector import PackedVector
from ..v31 import CdaeV31
from ...numerics import *
    


def _strip_namespaces(elem: ET.Element):
    if "}" in elem.tag:
        elem.tag = elem.tag.split("}", 1)[1]
    for child in elem:
        _strip_namespaces(child)


def parse_array(xml: ET.Element, dtype=np.float32) -> NDArray:
    return np.fromstring(xml.text, dtype=dtype, sep=" ")


def parse_input(xml: ET.Element) -> Geometry.Triangles.Input:
    return Geometry.Triangles.Input(Semantic(xml.get("semantic")), xml.get("source")[1:], int(xml.get("offset", 0)), int(xml.get("set", 0)))


def parse_triangle(xml: ET.Element) -> Geometry.Triangles:
    result = Geometry.Triangles()

    result.indices = parse_array(xml.find(DaeTag.p), np.int32)
    inputlist = xml.findall(DaeTag.input)
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

    vertices = mesh.find(DaeTag.vertices)
    verticesKey = vertices.get("id")
    verticesSrc = vertices.find(DaeTag.input).get("source")[1:]
    result.sources[verticesKey] = result.sources[verticesSrc]

    trilist0 = mesh.findall(DaeTag.triangles)
    for tri in trilist0:
        result.triangles.append(parse_triangle(tri))

    trilist1 = mesh.findall(DaeTag.polylist)
    for tri in trilist1:
        result.triangles.append(parse_triangle(tri))

    return result


def parse_node(xml: ET.Element) -> Node:
    res = Node()
    #res.matrix = parse_array(xml.find(DaeTag.matrix))
    geometry = xml.find(DaeTag.instance_geometry)
    if geometry is not None:
        url = geometry.get("url")[1:]
        materials = geometry.find(DaeTag.bind_material).find(DaeTag.technique_common).findall(DaeTag.instance_material)
        matdict = {mat.get("symbol"): mat.get("target", "")[1:] for mat in materials}
        res.geometry = GeometryInstance(url, matdict)

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


def convert_geometry(geo: Geometry, cdae: CdaeV31) -> CdaeV31.Mesh:

    mesh = CdaeV31.Mesh()
    mesh.type = CdaeV31.MeshType.STANDARD

    def try_set_numpy_array(vector: PackedVector, semantic: Semantic, set: int = 0):
        array = geo.get_array(semantic, set)
        if array is not None:
            vector.set_numpy_array(array)

    try_set_numpy_array(mesh.verts, Semantic.VERTEX)
    try_set_numpy_array(mesh.tverts0, Semantic.TEXCOORD, 0)
    try_set_numpy_array(mesh.tverts1, Semantic.TEXCOORD, 1)
    try_set_numpy_array(mesh.norms, Semantic.NORMAL)
    try_set_numpy_array(mesh.colors, Semantic.COLOR)

    indices: list[int] = []
    regions: list[CdaeV31.Mesh.DrawRegion] = []

    start = 0
    for item in geo.triangles:
        material = cdae.get_material_index(item.materialName)
        count = len(item.indices)
        indices.extend(item.indices)
        regions.append(CdaeV31.Mesh.DrawRegion(start, count, material))
        start = count

    mesh.indices.set_numpy_array(np.array(indices, np.int32))
    mesh.draw_regions.pack_list(regions)

    return mesh
    


def convert(dae: Collada):
    cdae = CdaeV31()

    for mat in dae.materials:
        cdae.materials.append(convert_material(mat))

    for geo in dae.geometries:
        cdae.meshes.append(convert_geometry(geo, cdae))

    tree = cdae.unpack_tree()

    return cdae



class DaeReader:

    @staticmethod
    def read_from_stream(stream: BufferedReader):

        tree = ET.parse(stream)
        root = tree.getroot()
        _strip_namespaces(root)

        if (root.tag != DaeTag.COLLADA):
            raise Exception("XML data is not valid Collada.")
        
        dae = parse_collada(root)
        return convert(dae)


    @staticmethod
    def read_from_file(filepath: str) -> CdaeV31:

        with open(filepath, "rb") as f:
            return DaeReader.read_from_stream(f)