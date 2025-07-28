import struct
import numpy as np
import xml.etree.cElementTree as ET

from dataclasses import dataclass
from enum import Enum
from io import BufferedReader, TextIOWrapper
from numpy.typing import NDArray

from .cdae_v31 import CdaeV31
from .packed_vector import PackedVector
from .msgpack_reader import MsgpackReader
from .msgpack_writer import MsgpackWriter
from .numerics import *


UNITS = ["X","Y","Z","W"]


def make_id(name, suffix):
        return f"{name}_{suffix}"


def write_src_float(flat_array: NDArray[np.float32], xml: ET.Element, stride: int, name: str, invert: bool = False):
    
    xml_source = ET.SubElement(xml, "source", {"id": name})

    if invert:
        flat_array = -flat_array
    array_id = f"{name}_array"
    array_length = len(flat_array)

    xml_float_array = ET.SubElement(xml_source, "float_array", {
        "id": array_id,
        "count": str(array_length)
    })
    xml_float_array.text = " ".join(map(str, flat_array))

    pos_technique = ET.SubElement(xml_source, "technique_common")
    ET.SubElement(pos_technique, "accessor", {
        "source": f"#{array_id}",
        "count": str(array_length // stride),
        "stride": str(stride)
    }).extend([ET.Element("param", {"name": UNITS[n], "type": "float"}) for n in range(stride)])


def write_geometry(mesh: CdaeV31.Mesh, lib_geometries: ET.Element, mesh_index: int, materials: list[CdaeV31.Material], mesh_mat_names: list[CdaeV31.Material]):

    geom_id = f"mesh_{mesh_index}"
    geom = ET.SubElement(lib_geometries, "geometry", {"id": geom_id, "name": geom_id})
    mesh_elem = ET.SubElement(geom, "mesh")

    def try_write_src(vector: NDArray[np.float32], name: str, stride: int, invert = False) -> str:
        src_id = f"{geom_id}_{name}"
        if vector.size == 0:
            return None
        write_src_float(vector, mesh_elem, stride, src_id, invert)
        return src_id

    positions_id = try_write_src(mesh.verts.to_numpy_array(np.float32), "position", 3)
    normals_id = try_write_src(mesh.norms.to_numpy_array(np.float32), "normals", 3, True)
    uv0s_id = try_write_src(mesh.tverts0.to_numpy_array(np.float32), "uv0s", 2)
    uv1s_id = try_write_src(mesh.tverts1.to_numpy_array(np.float32), "uv1s", 2)
    color_id = try_write_src(mesh.get_vec4f_colors(), "colors", 4)

    # Vertices
    vert_id = make_id(geom_id, "vertices")
    vertices = ET.SubElement(mesh_elem, "vertices", {"id": vert_id})
    ET.SubElement(vertices, "input", {"semantic": "POSITION", "source": f"#{positions_id}"})

    # Triangles by draw region
    indices = mesh.indices.to_numpy_array(np.uint32)
    draw_regions = mesh.draw_regions.to_numpy_array(np.uint32).reshape(-1, 3)
    for draw_index, (start, count, mat_index) in enumerate(draw_regions):
        mat_name = f"mat_{mat_index}" if mat_index < len(materials) else "mat_0"
        mesh_mat_names.append(mat_name)
        tris = ET.SubElement(mesh_elem, "triangles", {
            "count": str(count // 3),
            "material": mat_name
        })

        ET.SubElement(tris, "input", {"semantic": "VERTEX", "source": f"#{vert_id}", "offset": "0"})
        ET.SubElement(tris, "input", {"semantic": "NORMAL", "source": f"#{normals_id}", "offset": "0"})
        if uv0s_id is not None:
            ET.SubElement(tris, "input", {"semantic": "TEXCOORD", "source": f"#{uv0s_id}", "offset": "0", "set": "0"})
        if uv1s_id is not None:
            ET.SubElement(tris, "input", {"semantic": "TEXCOORD", "source": f"#{uv1s_id}", "offset": "0", "set": "1"})
        if color_id is not None:
            ET.SubElement(tris, "input", {"semantic": "COLOR", "source": f"#{color_id}", "offset": "0"})

        p = ET.SubElement(tris, "p")
        for i in range(start, start + count):
            vi = indices[i]
            p.text = (p.text or "") + f"{vi} "


def write_to_tree(cdae: CdaeV31, dae: ET.Element):
    collada = dae

    asset = ET.SubElement(collada, "asset")
    ET.SubElement(asset, "contributor")
    ET.SubElement(asset, "created").text = "2025-07-08T00:00:00"
    ET.SubElement(asset, "modified").text = "2025-07-08T00:00:00"
    ET.SubElement(asset, "unit", {"name": "meter", "meter": "1"})
    ET.SubElement(asset, "up_axis").text = "Z_UP"

    lib_geometries = ET.SubElement(collada, "library_geometries")
    lib_materials = ET.SubElement(collada, "library_materials")
    lib_effects = ET.SubElement(collada, "library_effects")
    lib_visual_scenes = ET.SubElement(collada, "library_visual_scenes")
    scene = ET.SubElement(collada, "scene")
    ET.SubElement(scene, "instance_visual_scene", {"url": "#Scene"})

    visual_scene = ET.SubElement(lib_visual_scenes, "visual_scene", {"id": "Scene", "name": "Scene"})

    # Materials (names only)
    for i, mat in enumerate(cdae.materials):
        mat_id = f"mat_{i}"
        effect_id = f"{mat_id}_fx"

        xml_mat = ET.SubElement(lib_materials, "material", {"id": mat_id, "name": mat.name})
        ET.SubElement(xml_mat, "instance_effect", {"url": f"#{effect_id}"})
        ET.SubElement(lib_effects, "effect", {"id": effect_id})

    # Geometries
    mesh_mat_names: list[list[str]] = []
    for mesh_index, mesh in enumerate(cdae.meshes):
        mesh_mat_names_2 = []
        write_geometry(mesh, lib_geometries, mesh_index, cdae.materials, mesh_mat_names_2)
        mesh_mat_names.append(mesh_mat_names_2)


    cdae_tree = cdae.unpack_tree()
    cdae_node_translations = cdae.defaultTranslations.unpack_list(Vec3F)
    cdae_node_rotation = cdae.defaultRotations.unpack_list(Quat4I16)

    dae_translations = []
    dae_rotations = []

    #for i in range(len(cdae_tree.nodes)):
        

    # Build tree: recursively walk nodes and objects
    def process_node(node_index: int, node: CdaeV31.Node, parent_xml_node):
        node_name = cdae.names[node.nameIndex]
        xml_node = ET.SubElement(parent_xml_node, "node", {"id": node_name, "name": node_name, "type": "NODE"})

        #location = dae_translations[node_index]
        #axis = dae_rotations[node_index]
        #translate_str = f"{location.x} {location.y} {location.z}"
        #rotate_str = f"{axis.x} {axis.y} {axis.z} {angle_deg}"


        for obj_index, obj in cdae_tree.enumerate_objects(node_index):

            obj_name = cdae.names[obj.nameIndex]
            if obj_name != node_name:
                xml_obj_node = ET.SubElement(xml_node, "node", {"id": obj_name, "name": obj_name, "type": "NODE"})
            else:
                xml_obj_node = xml_node

            for mesh_index in cdae_tree.enumerate_mesh_indexes(obj_index):
                geom_url = f"#mesh_{mesh_index}"
                mat_names = mesh_mat_names[mesh_index]

                inst_geom = ET.SubElement(xml_obj_node, "instance_geometry", {"url": geom_url})
                bind_mat = ET.SubElement(inst_geom, "bind_material")
                tech_common = ET.SubElement(bind_mat, "technique_common")

                for mat_name in mat_names:
                    ET.SubElement(tech_common, "instance_material", {
                        "symbol": mat_name,
                        "target": f"#{mat_name}"
                    })


        for child_index, child in cdae_tree.enumerate_nodes(node_index):
            process_node(child_index, child, xml_node)


    for node_index, node in cdae_tree.enumerate_root():
        process_node(node_index, node, visual_scene)


def write_to_stream(cdae: CdaeV31, f: TextIOWrapper):
    dae = ET.Element("COLLADA")
    dae.set("version", "1.4.1")
    dae.set("xmlns", "http://www.collada.org/2005/11/COLLADASchema")
    write_to_tree(cdae, dae)
    tree = ET.ElementTree(dae)
    ET.indent(tree, space="  ", level=0)  # Only available in Python 3.9+
    tree.write(f, encoding="unicode", xml_declaration=True)


def write_to_file(cdae: CdaeV31, filepath: str):

    with open(filepath, 'wt') as f:
        write_to_stream(cdae, f)