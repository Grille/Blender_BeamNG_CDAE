import bpy
import bmesh
import re
import numpy as np

from numpy.typing import NDArray
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from .cdae_v31 import *
from .blender_object_properties import ObjectProperties, ObjectRole
from .cdae_builder_tree import CdaeTree


class CdaeMaterialIndexer:
    def __init__(self):
        self.material_to_index = {}
        self.materials: list[bpy.types.Material] = []


    def get_index(self, bmat: bpy.types.Material):
        if bmat is None:
            return 0
        if bmat not in self.material_to_index:
            index = len(self.materials)
            self.material_to_index[bmat] = index
            self.materials.append(bmat)
        return self.material_to_index[bmat]
    
    

class CdeaMeshBuilder:

    def __init__(self, material_indexer: CdaeMaterialIndexer):
        self.mesh: bpy.types.Mesh = None
        self.scale = Vec3F(1,1,1)
        self.material_indexer = material_indexer


    def get_vtx_indices(self):
        loop_vertex_indices = np.empty(len(self.mesh.loops), dtype=np.int32)
        self.mesh.loops.foreach_get("vertex_index", loop_vertex_indices)
        return loop_vertex_indices


    def map_vtx_to_loop(self, vtx_data: NDArray, size: int, indices):
        vtx_data = vtx_data.reshape((-1, size))
        return vtx_data[indices]
    

    def get_vtx_data(self, key: str, size: int, indices):
        vertex_data = np.empty(len(self.mesh.vertices) * size, dtype=np.float32)
        self.mesh.vertices.foreach_get(key, vertex_data)
        return self.map_vtx_to_loop(vertex_data, size, indices)


    def get_loop_data(self, key: str, size: int):
        loop_data = np.empty(len(self.mesh.loops) * size, dtype=np.float32)
        self.mesh.loops.foreach_get(key, loop_data)
        return loop_data.reshape((-1, size))


    def get_uv_data(self, index = 0):
        if len(self.mesh.uv_layers) > index:
            uv_layer0 = self.mesh.uv_layers[index].data
            uv_data0 = np.empty(len(uv_layer0) * 2, dtype=np.float32)
            uv_layer0.foreach_get("uv", uv_data0)
            uv_data0 = uv_data0.reshape((-1, 2))
            uv_data0[:, 1] = 1.0 - uv_data0[:, 1]
            return uv_data0
        else:
            return None
        

    def get_color_data(self, indices):

        if len(self.mesh.color_attributes) > 0:
            layer_name = self.mesh.color_attributes[0].name
        else:
            return None 
    
        color_layer = self.mesh.color_attributes.get(layer_name)
        if not color_layer:
            return None

        loop_count = len(self.mesh.loops)
        vert_count = len(self.mesh.vertices)
        components = 4

        if color_layer.domain == 'CORNER':
            raw = np.empty(loop_count * components, dtype=np.float32)
            color_layer.data.foreach_get("color", raw)
            colors = raw.reshape((loop_count, components))

        elif color_layer.domain == 'POINT':
            raw = np.empty(vert_count * components, dtype=np.float32)
            color_layer.data.foreach_get("color", raw)
            colors = raw.reshape((vert_count, components))

            colors = colors[indices]

        else:
            return None

        colors_u8 = (colors * 255.0).astype(np.uint8)
        return colors_u8
        

    def build_from_mesh(self, mesh: bpy.types.Mesh)-> CdaeV31.Mesh:

        if any(len(p.vertices) > 4 for p in mesh.polygons):
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces)
            bm.to_mesh(mesh)
            bm.free()

        self.mesh = mesh
        mesh.calc_loop_triangles()
        mesh.calc_tangents()

        vertex_indices = self.get_vtx_indices()
        loop_positions = self.get_vtx_data("co", 3, vertex_indices)
        loop_normals = self.get_loop_data("normal", 3)
        #loop_tangents = self.get_loop_data("tangent", 4)
        loop_uvs0 = self.get_uv_data(0)
        loop_uvs1 = self.get_uv_data(1)
        loop_colors = self.get_color_data(vertex_indices)


        material_ranges: defaultdict[int, list] = defaultdict(list)
        for tri in mesh.loop_triangles:
            poly = mesh.polygons[tri.polygon_index]
            mat = mesh.materials[poly.material_index] if poly.material_index < len(mesh.materials) else None
            global_mat_index = self.material_indexer.get_index(mat)

            material_ranges[global_mat_index].append([
                tri.loops[2],
                tri.loops[1],
                tri.loops[0]
            ])

        
        indices_list = []
        for mat_index in material_ranges:
            range = material_ranges[mat_index]
            indices_list.extend(range)
        indices = np.array(indices_list, dtype=np.int32)


        draw_regions = []
        offset = 0
        for mat_index in material_ranges:
            count = len(material_ranges[mat_index])
            draw_regions.append((offset * 3, count * 3, mat_index))
            offset += count

        DrawRegion = np.dtype([
            ('elements_start', np.int32),
            ('elements_count', np.int32),
            ('material_index', np.int32),
        ])
        draw_region_array = np.array(draw_regions, dtype=DrawRegion)



        mesh_out = CdaeV31.Mesh()
        mesh_out.type = CdaeV31.MeshType.STANDARD

        mesh_out.verts.set_numpy_array(loop_positions)
        mesh_out.norms.set_numpy_array(loop_normals)
        #mesh_out.tangents.set_numpy_array(loop_tangents)
        mesh_out.indices.set_numpy_array(indices)
        mesh_out.draw_regions.set_numpy_array(draw_region_array)

        if loop_uvs0 is not None:
            mesh_out.tverts0.set_numpy_array(loop_uvs0)

        if loop_uvs1 is not None:
            mesh_out.tverts1.set_numpy_array(loop_uvs1)

        if loop_colors is not None:
            mesh_out.colors.set_numpy_array(loop_colors)

        mesh_out.numFrames = 1
        mesh_out.numMatFrames = 1
        mesh_out.vertsPerFrame = len(loop_positions)

        mins = loop_positions.min(axis=0).astype(float)
        maxs = loop_positions.max(axis=0).astype(float)
        mesh_out.bounds = Box6F(*mins, *maxs)

        return mesh_out


    def build_from_object(self, obj: bpy.types.Object | None) -> CdaeV31.Mesh:
        if obj is None:
            null = CdaeV31.Mesh()
            return null
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj: bpy.types.Object = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        try:
            return self.build_from_mesh(mesh)
        finally:
            eval_obj.to_mesh_clear()



class CdaeKeyframeSampler:

    @dataclass
    class Result:
        transforms: Transforms
        has_keyframes: bool



    def __init__(self):
        self.start: int = 0
        self.end: int = 100
        self.sample_count: int = 2
        self.duration = 0.0
        self.sample_transforms_enabled: bool = True
        self.sample_keyframes_enabled: bool = False
        self.keyframes: list[Transforms] = []
        self.nodes_enabled: list[bool] = []


    def create_sequence(self) -> CdaeV31.Sequence:
        seq = CdaeV31.Sequence()

        print("seq")

        for en in self.nodes_enabled:
            print(en)
        seq.numKeyframes = self.sample_count
        seq.duration = self.duration
        seq.translationMatters = self.nodes_enabled
        seq.rotationMatters = self.nodes_enabled
        return seq


    def sample(self, obj: bpy.types.Object | None):
        transforms_enabled = obj is not None and self.sample_transforms_enabled
        keyframes_enabled = obj is not None and self.sample_keyframes_enabled
        transforms = self.sample_current(obj) if transforms_enabled else Transforms()
        if keyframes_enabled:
            self.sample_keyframes(obj)
        else:
            self.nodes_enabled.append(False)
        return CdaeKeyframeSampler.Result(transforms, keyframes_enabled)



    def sample_keyframes(self, obj: bpy.types.Object):
        
        frame_backup = bpy.context.scene.frame_current

        frame_range = self.end - self.start
        frame_scale = frame_range / self.sample_count

        for iframe in (range(self.sample_count)):
            scaled_frame = iframe * frame_scale
            final_frame = scaled_frame + self.start
            self.keyframes.append(self.sample_frame(obj, final_frame))

        bpy.context.scene.frame_set(frame_backup)

        self.nodes_enabled.append(True)


    def sample_frame(self, obj: bpy.types.Object, frame: float) -> Transforms:
        intframe = int(frame)
        subframe = frame - intframe
        bpy.context.scene.frame_set(intframe, subframe=subframe)
        return self.sample_current(obj)
    

    def sample_current(self, obj: bpy.types.Object) -> Transforms:
        return Transforms.from_blender_matrix(obj.matrix_world)


class CdeaBuilder:
    
    def __init__(self):
        self.cdae = CdaeV31()
        self.tree = CdaeTree()
        self.material_indexer = CdaeMaterialIndexer()
        self.mesh_builder = CdeaMeshBuilder(self.material_indexer)
        self.sampler = CdaeKeyframeSampler()
        self.materials: list[bpy.types.Material] = []
        self.apply_scale: bool = True


    def build(self):

        cdae = self.cdae

        flat_tree = cdae.unpack_tree()
        flat_meshes = cdae.meshes

        defaultRotations = []
        defaultTranslations = []

        def add_node(node: CdaeTree.Node, parent_index: int = -1) -> int:
            
            node_samples = self.sampler.sample(node.bpy_sample_obj)
            trans = node_samples.transforms
            defaultRotations.append(trans.rotation)
            defaultTranslations.append(trans.translation)
            scale = trans.scale if self.apply_scale else Vec3F(1,1,1)

            (node_index, flat_node) = flat_tree.create_node()
            flat_tree.link_node(parent_index, node_index)
            flat_node.nameIndex = cdae.get_name_index(node.name)

            for obj in node.objects:
                (obj_index, flat_obj) = flat_tree.create_object()
                flat_tree.link_object(node_index, obj_index)
                flat_obj.nameIndex = cdae.get_name_index(obj.name)

                flat_obj.numMeshes = len(obj.meshes)
                flat_obj.startMeshIndex = len(flat_meshes)
   
                for mesh in obj.meshes:
                    flat_meshes.append(self.mesh_builder.build_from_object(mesh.bpy_mesh_obj))

            for child in node.nodes:
                add_node(child, node_index)

            return node_index

        
        shapes = cdae.unpack_subshapes()
        shapes_dict: dict[CdaeTree.SubShape, int] = {}
        for key, shape in self.tree.shapes.items():
            
            print(key)
            first_node = len(flat_tree.nodes)
            first_obj = len(flat_tree.objects)

            for node in shape.nodes:
                add_node(node)

            last_node = len(flat_tree.nodes)
            last_obj = len(flat_tree.objects)
            node_count = last_node-first_node
            obj_count = last_obj-first_obj

            if node_count > 0 or obj_count > 0:
                shapes_dict[shape] = len(shapes)
                shapes.append(CdaeV31.SubShape(first_node, first_obj, node_count, obj_count))


        details = cdae.unpack_details()
        for key, detail in self.tree.details.items():
            shapeidx = shapes_dict.get(detail.shape, -1)
            detail.template.nameIndex = self.cdae.get_name_index(key)
            detail.template.subShapeNum = shapeidx
            details.append(detail.template)


        if self.sampler.sample_keyframes_enabled:
            seq = self.sampler.create_sequence()
            cdae.sequences.append(seq)
            seq.nameIndex = self.cdae.get_name_index("ambiant")

            print(f"ANIM {len(self.sampler.keyframes)}")
            kf_loc = []
            kf_rot = []
            kf_scl = []
            for frame in self.sampler.keyframes:
                kf_loc.append(frame.translation)
                kf_rot.append(frame.rotation)
                kf_scl.append(frame.scale)

            self.cdae.nodeTranslations.pack_list(kf_loc)
            self.cdae.nodeRotations.pack_list(kf_rot)
            self.cdae.nodeAlignedScales.pack_list(kf_scl)
            

        for mat in self.material_indexer.materials:
            res = CdaeV31.Material()
            self.cdae.materials.append(res)
            if mat is None:
                res.name = "undefined"
            else:
                res.name = mat.name

        self.cdae.defaultRotations.pack_list(defaultRotations)
        self.cdae.defaultTranslations.pack_list(defaultTranslations)

        states = [CdaeV31.ObjectState() for _ in flat_tree.objects]
        self.cdae.pack_states(states)

        # Convert flat_nodes and flat_objects into PackedVectors
        self.cdae.pack_tree(flat_tree)
        self.cdae.pack_subshapes(shapes)
        self.cdae.pack_details(details)
        self.cdae.meshes = flat_meshes

        self.materials = self.material_indexer.materials