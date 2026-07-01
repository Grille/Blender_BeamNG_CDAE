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


def parse_array_text(text: str | None, dtype=np.float32) -> NDArray:
    if text is None:
        array = np.empty(0, dtype=dtype)
    else:
        array = np.fromstring(text, dtype=dtype, sep=" ")
    return array


def parse_float_array(xml: ET.Element) -> NDArray[np.float32]:
    #count = int(xml.get(DaeAttributes.COUNT))
    array = parse_array_text(xml.text)
    return array


def parse_input(xml: ET.Element) -> Geometry.Triangles.Input:
    return Geometry.Triangles.Input(Semantic(xml.get("semantic")), xml.get("source")[1:], int(xml.get("offset", 0)), int(xml.get("set", 0)))


def parse_triangles(xml: ET.Element, parent: Geometry) -> Geometry.Triangles:
    result = Geometry.Triangles(parent)

    result.material_name = xml.get(DaeAttributes.MATERIAL)
    result.triangle_count = int(xml.get(DaeAttributes.COUNT))

    result.indices = parse_array_text(xml.find(DaeTag.p).text, np.int32)

    inputlist = xml.findall(DaeTag.input)
    for input in inputlist:
        result.inputs.append(parse_input(input))

    return result


def parse_polylist(xml: ET.Element, parent: Geometry)-> Geometry.Triangles:
    result = parse_triangles(xml, parent)

    vcount = parse_array_text(xml.find(DaeTag.vcount).text, np.int32)
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


def parse_geometry(xml: ET.Element) -> Geometry:
    result = Geometry()
    result.name = xml.get("name")
    mesh = xml.find(DaeTag.mesh)

    srclist = mesh.findall(DaeTag.source)
    for src in srclist:
        key = src.get("id")
        array = parse_float_array(src.find(DaeTag.float_array))
        accessor = src.find(DaeTag.technique_common).find(DaeTag.accessor)
        count = int(accessor.get(DaeAttributes.COUNT))
        stride = int(accessor.get(DaeAttributes.STRIDE))
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


def parse_node(xml: ET.Element) -> Node:
    res = Node()
    res.name = xml.get("name")

    geometry = xml.find(DaeTag.instance_geometry)
    if geometry is not None:
        url = geometry.get("url")[1:]
        materials = geometry.find(DaeTag.bind_material).find(DaeTag.technique_common).findall(DaeTag.instance_material)
        matdict = {mat.get("symbol"): mat.get("target", "")[1:] for mat in materials}
        res.geometry_instance = GeometryInstance(url, matdict)

    matrix = xml.find(DaeTag.matrix)
    if matrix is not None:
        res.matrix = DaeMatrix(parse_array_text(matrix.text))
    else:
        res.matrix = None

    nodelist = xml.findall(DaeTag.node)
    for node in nodelist:
        id = node.get("id")
        res.children[id] = parse_node(node)

    return res


def parse_collada(xml: ET.Element) -> Collada:
    dae = Collada()

    dae.unit_meter = float(xml.find(DaeTag.asset).find(DaeTag.unit).get(DaeAttributes.METER))
    
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
        print(f"fetch {item.material_name}")
        material = cdae.get_material_index(material_dict.get(item.material_name, "mat_0"), True)
        vtx_count = item.triangle_count * 3
        print(item.triangle_count)
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
            print(translation)
            rotation = Quat4I16.from_collada_quaternion(matrix.to_quaternion())
        else:
            translation = Vec3F()
            rotation = Quat4I16.create_identity()
        
        (node_index, _) = flat_tree.create_node(node.name, parent_index, translation, rotation)

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
        
        dae = parse_collada(root)
        return convert(dae)


    @staticmethod
    def read_from_file(filepath: str) -> CdaeV31:

        with open(filepath, "rb") as f:
            return DaeReader.read_from_stream(f)