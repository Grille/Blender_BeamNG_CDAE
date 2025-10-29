import struct
import numpy as np
import xml.etree.cElementTree as ET

from dataclasses import dataclass
from enum import Enum
from io import BufferedReader, TextIOWrapper
from numpy.typing import NDArray

from .cdae_v31 import CdaeV31
from .numerics import *
from .debug import Stopwatch


@dataclass(frozen=True)
class Accessor:
    stride: int
    params: list[tuple[str, str]]

A_VEC2 = Accessor(2, [("X", "float"), ("Y", "float")])
A_VEC3 = Accessor(3, A_VEC2.params + [("Z", "float")])
A_VEC4 = Accessor(4, A_VEC3.params + [("W", "float")])
A_TIME = Accessor(1, [("TIME", "float")])
A_TRANSFORM = Accessor(16, [("TRANSFORM", "float4x4")])


limit_precision_enabled = False
limit_precision_dp = 4


def format_id(id: str):
    return id.replace(".", "_DOT_")


def format_float(value: float) -> str:
    return str(round(value, limit_precision_dp)) if limit_precision_enabled else str(value)


def format_float_list(values: list[float]) -> str:
    return " ".join(map(format_float, values))


def append_matrix(quat: Quat4F, location: Vec3F, scale: Vec3F, values: list[float]):
    matrix = quat.to_collada_matrix()
    matrix.translation = location.tuple3
    for col in range(4): 
        for row in range(4):
            values.append(matrix[col][row])


def get_matrix(quat: Quat4F, location: Vec3F):
    values: list[float] = []
    append_matrix(quat, location, Vec3F(1,1,1), values)
    return values


def make_id(name, suffix):
        return f"{name}_{suffix}"


def write_float_array(xml: ET.Element, flat_array: NDArray[np.float32], array_id: str):

    array_length = len(flat_array)
    xml_float_array = ET.SubElement(xml, "float_array", {
        "id": array_id,
        "count": str(array_length)
    })
    xml_float_array.text = format_float_list(flat_array)


def write_accessor(xml: ET.Element, source_id: str, count: int, accessor: Accessor):

    xml_technique = ET.SubElement(xml, "technique_common")
    ET.SubElement(xml_technique, "accessor", {
        "source": f"#{source_id}",
        "count": str(count),
        "stride": str(accessor.stride)
    }).extend([ET.Element("param", {"name": acc[0], "type": acc[1]}) for acc in accessor.params])


def write_src_float(xml: ET.Element, flat_array: NDArray[np.float32], name: str, accessor: Accessor):

    xml_source = ET.SubElement(xml, "source", {"id": name})
    array_id = f"{name}_array"
    write_float_array(xml_source, flat_array, array_id)
    write_accessor(xml_source, array_id, len(flat_array) // accessor.stride, accessor)


def write_geometry(mesh: CdaeV31.Mesh, lib_geometries: ET.Element, mesh_index: int, materials: list[CdaeV31.Material], mesh_mat_names: list[CdaeV31.Material]):

    geom_id = f"mesh_{mesh_index}"
    geom = ET.SubElement(lib_geometries, "geometry", {"id": geom_id, "name": geom_id})
    mesh_elem = ET.SubElement(geom, "mesh")

    def try_write_src(vector: NDArray[np.float32], name: str, accessor: Accessor) -> str:
        if vector.size == 0: return None
        src_id = f"{geom_id}_{name}"
        write_src_float(mesh_elem, vector, src_id, accessor)
        return src_id
    
    def try_write_src_uv(vector: NDArray[np.float32], name: str) -> str:
        if vector.size == 0: return None
        uv = vector.reshape(-1, 2).copy()   # copy -> writable, keeps both columns
        uv[:, 1] = 1.0 - uv[:, 1]           # invert V
        return try_write_src(uv.ravel(), name, A_VEC2)

    positions_id = try_write_src(mesh.verts.to_numpy_array(np.float32), "position", A_VEC3)
    normals_id = try_write_src(mesh.norms.to_numpy_array(np.float32), "normals", A_VEC3)
    uv0s_id = try_write_src_uv(mesh.tverts0.to_numpy_array(np.float32), "uv0s")
    uv1s_id = try_write_src_uv(mesh.tverts1.to_numpy_array(np.float32), "uv1s")
    color_id = try_write_src(mesh.get_vec4f_colors(), "colors", A_VEC4)

    # Vertices
    vert_id = make_id(geom_id, "vertices")
    vertices = ET.SubElement(mesh_elem, "vertices", {"id": vert_id})
    ET.SubElement(vertices, "input", {"semantic": "POSITION", "source": f"#{positions_id}"})

    # Triangles by draw region
    indices = mesh.indices.to_numpy_array(np.uint32)
    indices = indices.reshape(-1, 3)[:, [2, 1, 0]].ravel()
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

        ET.SubElement(tris, "p").text = " ".join(str(indices[i]) for i in range(start, start + count))


def write_animation(xml: ET.Element, target_id: str, times: list[float], transforms: list[float]):
    xml_anim = ET.SubElement(xml, "animation")

    src_input_id = f"{target_id}-anim-input"
    write_src_float(xml_anim, times, src_input_id, A_TIME)
    src_output_id = f"{target_id}-anim-output"
    write_src_float(xml_anim, transforms, src_output_id, A_TRANSFORM)

    sampler_id = f"{target_id}-sampler"
    xml_sampler = ET.SubElement(xml_anim, "sampler", {"id": sampler_id})
    ET.SubElement(xml_sampler,"input", {"semantic":"INPUT", "source":f"#{src_input_id}"})
    ET.SubElement(xml_sampler,"input", {"semantic":"OUTPUT", "source":f"#{src_output_id}"})

    ET.SubElement(xml_anim, "channel", {"source":f"#{sampler_id}", "target":f"{target_id}/transform"})


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
    default_translations = cdae.defaultTranslations.unpack_list(Vec3F)
    default_rotation = cdae.defaultRotations.unpack_list(Quat4I16)

    # Build tree: recursively walk nodes and objects
    def process_node(node_index: int, node: CdaeV31.Node, parent_xml_node):
        node_name = cdae.names[node.nameIndex]
        xml_node = ET.SubElement(parent_xml_node, "node", {"id": node_name, "name": node_name, "type": "NODE"})

        matrix = get_matrix(default_rotation[node_index], default_translations[node_index])
        ET.SubElement(xml_node, "matrix", {"sid": "transform"}).text = format_float_list(matrix)

        for obj_index, obj in cdae_tree.enumerate_child_objects(node_index):
 
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


        for child_index, child in cdae_tree.enumerate_child_nodes(node_index):
            process_node(child_index, child, xml_node)


    for node_index, node in cdae_tree.enumerate_root():
        process_node(node_index, node, visual_scene)


    if len(cdae.sequences) > 0:

        seq = cdae.sequences[0]
        lib_animations = ET.SubElement(collada, "library_animations")

        num_keyframes = seq.numKeyframes
        node_translations = cdae.nodeTranslations.unpack_list(Vec3F)
        node_rotation = cdae.nodeRotations.unpack_list(Quat4I16)

        keyframes_node_index = 0

        for node_index, node in enumerate(cdae_tree.nodes):

            if not seq.translationMatters[node_index]:
                continue

            keyframes_offset = keyframes_node_index * num_keyframes
            keyframes_node_index += 1

            times: list[float] = []
            transforms: list[float] = []

            for index in range(0, num_keyframes):

                progress = index / num_keyframes
                time = seq.duration * progress
                times.append(time)
                
                keyframe_index = index + keyframes_offset
                append_matrix(node_rotation[keyframe_index], node_translations[keyframe_index], Vec3F(1,1,1), transforms)

            times.append(seq.duration)
            append_matrix(node_rotation[keyframes_offset], node_translations[keyframes_offset], Vec3F(1,1,1), transforms)

            node_name = cdae.names[node.nameIndex]
            write_animation(lib_animations, node_name, times, transforms)

            
            


def write_to_stream(cdae: CdaeV31, f: TextIOWrapper):
    sw = Stopwatch()
    dae = ET.Element("COLLADA")
    dae.set("version", "1.4.1")
    dae.set("xmlns", "http://www.collada.org/2005/11/COLLADASchema")
    write_to_tree(cdae, dae)
    sw.log("xml_build")
    tree = ET.ElementTree(dae)
    ET.indent(tree, space="  ", level=0)  # Only available in Python 3.9+
    sw.log("xml_indent")
    tree.write(f, encoding="unicode", xml_declaration=True)
    sw.log("xml_write")
    sw.print()


def write_to_file(cdae: CdaeV31, filepath: str):

    with open(filepath, 'wt') as f:
        write_to_stream(cdae, f)