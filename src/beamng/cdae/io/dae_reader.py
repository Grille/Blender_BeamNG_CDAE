import struct

from dataclasses import dataclass
from enum import Enum
from io import BufferedReader
from numpy.typing import NDArray
from typing import TypeVar

from .dae import *
from ..packed_vector import PackedVector
from ..v31 import CdaeV31
from ...numerics import *

import numpy as np
import zstandard as zstd
import xml.etree.cElementTree as ET



def _strip_namespaces(elem: ET.Element):
    if "}" in elem.tag:
        elem.tag = elem.tag.split("}", 1)[1]
    for child in elem:
        _strip_namespaces(child)



class XmlReader:

    def __init__(self, element: ET.Element) -> None:
        self.element = element


    def _layout_error(self): return Exception()


    def get(self, key: str, default: str | None = None) -> str:
        value = self.element.get(key, default)
        if value is None: raise self._layout_error()
        return value


    def get_int(self, key: str, default: int | None = None):
        value = self.element.get(key)
        if value is not None: return int(value)
        elif default is not None: return default
        raise self._layout_error()


    def get_float(self, key: str, default: float | None = None):
        value = self.element.get(key)
        if value is not None: return float(value)
        elif default is not None: return default
        raise self._layout_error()


    def find(self, *path: str):
        element = self.element
        for name in path:
            element = element.find(name)
            if element is None: raise self._layout_error()
        return XmlReader(element)


    def find_optional(self, *path: str):
        element = self.element
        for name in path:
            element = element.find(name)
            if element is None: return None
        return XmlReader(element)


    def findall(self, path: str):
        items = self.element.findall(path)
        return [XmlReader(item) for item in items]


    def parse_array(self, dtype: np.typing.DTypeLike=np.float32):
        if self.text is None:
            array = np.empty(0, dtype=dtype)
        else:
            array = np.fromstring(self.text, dtype=dtype, sep=" ")
        return array


    @property
    def text(self): return self.element.text



def parse_input(xml: XmlReader) -> Geometry.Triangles.Input:
    return Geometry.Triangles.Input(Semantic(xml.get("semantic")), xml.get("source")[1:], xml.get_int("offset", 0), xml.get_int("set", 0))


def parse_triangles(xml: XmlReader, parent: Geometry) -> Geometry.Triangles:
    triangle_count = xml.get_int(DaeAttributes.COUNT)
    material_name = xml.get(DaeAttributes.MATERIAL)
    indices = xml.find(DaeTag.p).parse_array(np.int32)

    inputlist = xml.findall(DaeTag.input)
    inputs = [parse_input(input) for input in inputlist]

    return Geometry.Triangles(parent, triangle_count, material_name, indices, inputs)


def parse_polylist(xml: XmlReader, parent: Geometry)-> Geometry.Triangles:
    result = parse_triangles(xml, parent)

    vcount = xml.find(DaeTag.vcount).parse_array(np.int32)
    triangle_indices: list[int] = []
    stride = result.stride

    def copy(index: int):
        sidx = index * stride
        for i in range(0, stride):
            triangle_indices.append(result.indices[sidx + i])

    triangle_count = 0
    cursor = 0
    for n in vcount:
        for i in range(1, n - 1):
            triangle_count += 1
            copy(cursor)
            copy(cursor + i)
            copy(cursor + i + 1)
        cursor += n

    result.indices = np.array(triangle_indices, dtype=np.int32)
    result.triangle_count = triangle_count

    return result


def parse_geometry(xml: XmlReader) -> Geometry:
    result = Geometry()
    result.name = xml.get("name")
    mesh = xml.find(DaeTag.mesh)

    srclist = mesh.findall(DaeTag.source)
    for src in srclist:
        key = src.get("id")
        array = src.find(DaeTag.float_array).parse_array()
        accessor = src.find(DaeTag.technique_common, DaeTag.accessor)
        count = accessor.get_int(DaeAttributes.COUNT)
        stride = accessor.get_int(DaeAttributes.STRIDE)
        result.sources[key] = Geometry.Source(array, count, stride)

    vertices = mesh.find(DaeTag.vertices)
    verticesKey = vertices.get("id")
    verticesSrc = vertices.find(DaeTag.input).get("source")[1:]
    result.sources[verticesKey] = result.sources[verticesSrc]

    trilist0 = mesh.findall(DaeTag.triangles)
    for tri in trilist0:
        result.triangles.append(parse_triangles(tri, result))

    trilist1 = mesh.findall(DaeTag.polylist)
    for tri in trilist1:
        result.triangles.append(parse_polylist(tri, result))

    return result


def parse_node(xml: XmlReader) -> Node:
    res = Node()
    res.name = xml.get("name")

    geometry = xml.find_optional(DaeTag.instance_geometry)
    if geometry is not None:
        url = geometry.get("url")[1:]
        materials = geometry.find(DaeTag.bind_material, DaeTag.technique_common).findall(DaeTag.instance_material)
        matdict = {mat.get("symbol"): mat.get("target", "")[1:] for mat in materials}
        res.geometry_instance = GeometryInstance(url, matdict)

    matrix = xml.find_optional(DaeTag.matrix)
    if matrix is not None:
        res.matrix = DaeMatrix(matrix.parse_array())
    else:
        res.matrix = None

    nodelist = xml.findall(DaeTag.node)
    for node in nodelist:
        id = node.get("id")
        res.children[id] = parse_node(node)

    return res


def parse_collada(xml: XmlReader) -> Collada:
    dae = Collada()

    dae.unit_meter = xml.find(DaeTag.asset, DaeTag.unit).get_float(DaeAttributes.METER)
    
    matlib = xml.find(DaeTag.library_materials)
    matlist = matlib.findall(DaeTag.material)
    for mat in matlist:
        id = mat.get("id")
        dae.materials[id] = Material(mat.get("name"))

    geolib = xml.find(DaeTag.library_geometries)
    geolist = geolib.findall(DaeTag.geometry)
    for geo in geolist:
        id = geo.get("id")
        dae.geometries[id] = parse_geometry(geo)

    scnlib = xml.find(DaeTag.library_visual_scenes)
    scn = scnlib.find(DaeTag.visual_scene)
    nodelist = scn.findall(DaeTag.node)
    for node in nodelist:
        id = node.get("id")
        dae.nodes[id] = parse_node(node)
    
    return dae


def convert_material(daemat: Material) -> CdaeV31.Material:
    mat = CdaeV31.Material()
    mat.name = daemat.name
    return mat


def convert_geometry(geo: Geometry, material_dict: dict[str,str], cdae: CdaeV31, scale: float) -> CdaeV31.Mesh:

    mesh = CdaeV31.Mesh()
    mesh.type = CdaeV31.MeshType.STANDARD

    regions: list[CdaeV31.Mesh.DrawRegion] = []

    vtx_offset = 0
    for item in geo.triangles:
        material = cdae.get_material_index(material_dict.get(item.material_name, "mat_0"), True)
        vtx_count = item.triangle_count * 3
        region = CdaeV31.Mesh.DrawRegion(vtx_offset, vtx_count, material)
        regions.append(region)
        vtx_offset += vtx_count

    if vtx_offset == 0:
        mesh.type = CdaeV31.MeshType.NULL
        return mesh
    
    # array mesh
    dst_verts = np.zeros((vtx_offset, 3), np.float32)
    dst_norms = np.zeros((vtx_offset, 3), np.float32)
    dst_tverts0 = np.zeros((vtx_offset, 2), np.float32)
    dst_tverts1 = np.zeros((vtx_offset, 2), np.float32)
    dst_colors = np.ones((vtx_offset, 4), np.float32)
    dst_indices = np.arange(vtx_offset, dtype=np.int32)

    tverts0_enabled = False
    tverts1_enabled = False
    colors_enabled = False

    vtx_offset = 0
    for item in geo.triangles:
        src_verts = item.get_indexed_array(Semantic.VERTEX)
        src_norms = item.get_indexed_array(Semantic.NORMAL)
        src_tverts0 = item.get_indexed_array(Semantic.TEXCOORD, 0)
        src_tverts1 = item.get_indexed_array(Semantic.TEXCOORD, 1)
        src_colors = item.get_indexed_array(Semantic.COLOR)

        next_vtx_offset = vtx_offset + item.triangle_count * 3

        dst_verts[vtx_offset:next_vtx_offset] = src_verts 

        if src_norms is not None:
            dst_norms[vtx_offset:next_vtx_offset] = src_norms

        if src_tverts0 is not None:
            dst_tverts0[vtx_offset:next_vtx_offset] = src_tverts0
            tverts0_enabled = True

        if src_tverts1 is not None:
            dst_tverts1[vtx_offset:next_vtx_offset] = src_tverts1
            tverts1_enabled = True

        if src_colors is not None:
            dst_colors[vtx_offset:next_vtx_offset] = src_colors
            colors_enabled = True

        vtx_offset = next_vtx_offset

    dst_indices = dst_indices.reshape(-1, 3)[:, [2, 1, 0]]
    dst_verts[:, 0:2] *= -1
    dst_norms[:, 0:2] *= -1

    mesh.verts.set_numpy_array(dst_verts * scale)
    mesh.norms.set_numpy_array(dst_norms)
    mesh.indices.set_numpy_array(dst_indices)
    mesh.draw_regions.pack_list(regions)

    if tverts0_enabled:
        mesh.tverts0.set_numpy_array(dst_tverts0)
    if tverts1_enabled:
        mesh.tverts1.set_numpy_array(dst_tverts1)
    if colors_enabled:
        mesh.set_vec4_colors(dst_colors)

    return mesh


def convert(dae: Collada):
    cdae = CdaeV31()

    material_dict: dict[str, str] = {}
    for mat_id in dae.materials:
        mat = dae.materials[mat_id]
        cdae.materials.append(convert_material(mat))
        material_dict[mat_id] = mat.name
        print(f"assign {mat_id} {mat.name}")


    geometry_idx_dict: dict[str, int] = {}
    for idx, geo_id in enumerate(dae.geometries):
        geo = dae.geometries[geo_id]
        cdae.meshes.append(convert_geometry(geo, material_dict, cdae, dae.unit_meter))
        geometry_idx_dict[geo_id] = idx


    flat_tree = cdae.unpack_tree()

    def add_node(node: Node, parent_index: int = -1) -> int:

        if node.matrix is not None:
            matrix = node.matrix.to_matrix()
            translation = Vec3F.from_list3(matrix.to_translation())
            scale = Vec3F.from_list3(matrix.to_scale())
            rotation = Quat4I16.from_collada_quaternion(matrix.to_quaternion())
            transforms = Transforms(translation, scale, rotation)
        else:
            transforms = Transforms.IDENTITY
        
        (node_index, _) = flat_tree.create_node(node.name, parent_index, transforms)

        if node.geometry_instance is not None:

            url = node.geometry_instance.url
            geometry_name = dae.geometries[url].name
            mesh_idx = geometry_idx_dict[url]

            (_, flat_obj) = flat_tree.create_object(geometry_name, node_index)

            flat_obj.numMeshes = 1
            flat_obj.startMeshIndex = mesh_idx

        for child_id in node.children:
            add_node(node.children[child_id], node_index)

        return node_index
    
    for root_node_id in dae.nodes:
        add_node(dae.nodes[root_node_id])

    cdae.pack_tree(flat_tree)
    

    return cdae



class DaeReader:

    @staticmethod
    def read_from_stream(stream: BufferedReader):

        tree = ET.parse(stream)
        root = tree.getroot()
        _strip_namespaces(root)

        if (root.tag != DaeTag.COLLADA):
            raise Exception("XML data is not valid Collada.")
        
        dae = parse_collada(XmlReader(root))
        return convert(dae)


    @staticmethod
    def read_from_file(filepath: str) -> CdaeV31:

        with open(filepath, "rb") as f:
            return DaeReader.read_from_stream(f)