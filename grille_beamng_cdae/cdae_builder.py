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


# Classes to help build serializable CdaeV31.


class CdaeNodeList:

    def __init__(self, nodes: 'list[CdaeTree.Node]'):
        self.nodes = nodes


    def get_child_node(self, name: str) -> 'CdaeTree.Node':

        for node in self.nodes:
            if node.name == name:
                return node
            
        node = CdaeTree.Node(name, [], [])
        self.nodes.append(node)
        return node
    

    def print_nodes_recursive(self, indent = 0):
        istr = ' '*indent
        if indent > 8:
            print(istr+"...")
            return
        print(istr+"[")
        for node in self.nodes:
            print(istr+node.name)
            node.print_nodes_recursive(indent + 1)
        print(istr+"]")
        pass


class CdaeTree(CdaeNodeList):

    class Node(CdaeNodeList):

        def __init__(self, name: str, nodes: 'list[CdaeTree.Node]', objects: 'list[CdaeTree.Object]'):

            super().__init__(nodes)
            self.bpy_obj: bpy.types.Object = None
            self.name = name
            self.objects = objects
            self.position = Vec3F()
            self.rotation = Quat4I16()


        def get_object(self, name: str = None):
            if name is None:
                name = self.name
            for obj in self.objects:
                if obj.name == name:
                    return obj
            obj = CdaeTree.Object(name)
            self.objects.append(obj)
            return obj
        

        def append_mesh(self, obj):
            mesh = CdaeTree.Mesh(obj)
            self.get_object().meshes.append(mesh)
            matrix = obj.matrix_world
            self.position = Vec3F.from_list3(matrix.to_translation())
            self.rotation = Quat4I16.from_blender_quaternion(matrix.to_quaternion())


        def enumerate_meshes(self):

            for obj in self.objects:
                for mesh in obj.meshes:
                    yield mesh

            for node in self.nodes:
                yield from node.enumerate_meshes()



    class Object:

        def __init__(self, name: str):
            self.name = name
            self.meshes: list[CdaeTree.Mesh] = []
    


    class Mesh:
        def __init__(self, obj: bpy.types.Object):
            self.bpy_obj = obj
            self.scale = Vec3F()



    def __init__(self):
        super().__init__([])
        self.build_scene_tree = True


    def enumerate_meshes(self):
        for node in self.nodes:
            yield from node.enumerate_meshes()


    def add_selected(self):
        self.add_objects(set(bpy.context.selected_objects))


    def get_node_by_path(self, path: str) -> 'CdaeTree.Node':

        split_path = re.split(r'[\\/\.]', path)
        if len(split_path) == 0:
            raise Exception("no path")
        
        node = self.get_child_node(split_path[0])
        for key in split_path[1:]:
            node = node.get_child_node(key)

        return node


    def add_object(self, obj: bpy.types.Object):

        has_mesh = ObjectProperties.has_mesh(obj)

        if not self.build_scene_tree:
            name = obj.name
            node = self.get_node_by_path(name)
            if has_mesh:
                node.append_mesh(obj)
            return

        role = ObjectRole.from_obj(obj)
        lod_size = getattr(obj, ObjectProperties.LOD_SIZE)
        namespace = "base00.start01"

        if role == ObjectRole.Generic:
            path = getattr(obj, ObjectProperties.PATH)
            node = self.get_node_by_path(path)
            if has_mesh:
                node.append_mesh(obj)

        elif role == ObjectRole.Collision:
            path = f"{namespace}.colmesh-1"
            self.get_node_by_path(path).append_mesh(obj)

        elif role == ObjectRole.Mesh:
            path = f"{namespace}.model{lod_size}"
            self.get_node_by_path(path).append_mesh(obj)
            
        elif role == ObjectRole.Billboard:
            bb = "bbz" if getattr(obj, ObjectProperties.BB_FLAG0) else "bb"
            path = f"{namespace}.{bb}_billboard{lod_size}"
            self.get_node_by_path(path).append_mesh(obj)

        elif role == ObjectRole.AutoBillboard:
            path = f"{namespace}.bb_autobillboard{lod_size}"
            self.get_node_by_path(path)

        elif role == ObjectRole.NullDetail:
            path = f"{namespace}.nulldetail{lod_size}"
            self.get_node_by_path(path)



    def add_objects(self, objects: set[bpy.types.Object]):
        for obj in objects: self.add_object(obj)


    @staticmethod
    def from_objects(objects: set[bpy.types.Object]) -> 'CdaeTree':
        tree = CdaeTree()
        tree.add_objects(objects)
        return tree
    

    @staticmethod
    def from_selection() -> 'CdaeTree':
        selected = set(bpy.context.selected_objects)
        return CdaeTree.from_objects(selected)



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

    def __init__(self):
        self.mesh: bpy.types.Mesh = None


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
            return uv_data0.reshape((-1, 2))
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
        

    def build_from_mesh(self, mesh: bpy.types.Mesh, material_indexer: CdaeMaterialIndexer)-> CdaeV31.Mesh:

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
        loop_tangents = self.get_loop_data("tangent", 4)
        loop_uvs0 = self.get_uv_data(0)
        loop_uvs1 = self.get_uv_data(1)
        loop_colors = self.get_color_data(vertex_indices)


        material_ranges: defaultdict[int, list] = defaultdict(list)
        for tri in mesh.loop_triangles:
            poly = mesh.polygons[tri.polygon_index]
            mat = mesh.materials[poly.material_index] if poly.material_index < len(mesh.materials) else None
            global_mat_index = material_indexer.get_index(mat)

            material_ranges[global_mat_index].append([
                tri.loops[0],
                tri.loops[1],
                tri.loops[2]
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

        loop_normals = -loop_normals

        mesh_out.verts.set_numpy_array(loop_positions)
        mesh_out.norms.set_numpy_array(loop_normals)
        mesh_out.encoded_norms.alloc(len(loop_positions))
        mesh_out.tangents.set_numpy_array(loop_tangents)
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

        return mesh_out


    def build_from_object(self, obj: bpy.types.Object, material_indexer: CdaeMaterialIndexer)-> CdaeV31.Mesh:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj: bpy.types.Object = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        try:
            return self.build_from_mesh(mesh, material_indexer)
        finally:
            eval_obj.to_mesh_clear()



class CdaeKeyframeSampler:

    def __init__(self):
        self.start: int = 0
        self.end: int = 100
        self.samples: int = 2


    def sample(self, obj: bpy.types.Object):
        
        frame_backup = bpy.context.scene.frame_current

        frame_range = self.end = self.start
        frame_scale = self.samples / frame_range

        matrices: list[mathutils.Matrix] = []

        for iframe in (range(self.samples)):
            scaled_frame = iframe * frame_scale
            final_frame = scaled_frame + self.start
            matrices.append(self.sample_frame(obj, final_frame))

        bpy.context.scene.frame_set(frame_backup)

        return matrices


    def sample_frame(self, obj: bpy.types.Object, frame: float) -> mathutils.Matrix:
        intframe = int(frame)
        subframe = frame - intframe
        bpy.context.scene.frame_set(intframe, subframe)
        return obj.matrix_world.copy()



class CdeaBuilder:
    
    def __init__(self):
        self.cdae = CdaeV31()
        self.tree = CdaeTree()
        self.animations_enabled: bool = False
        self.sampler = CdaeKeyframeSampler()
        self.materials: list[bpy.types.Material] = []
        self.use_transforms: bool = True
        self.apply_scale: bool = True


    def build(self):

        cdae = self.cdae

        flat_tree = cdae.unpack_tree()
        flat_meshes = cdae.meshes

        materials = CdaeMaterialIndexer()

        defaultRotations = []
        defaultTranslations = []

        def add_node(node: 'CdaeTree.Node', parent_index: int = -1) -> int:
            if self.use_transforms:
                defaultRotations.append(node.rotation)
                defaultTranslations.append(node.position)
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
                    mesh_builder = CdeaMeshBuilder()
                    flat_meshes.append(mesh_builder.build_from_object(mesh.bpy_obj, materials))

            for child in node.nodes:
                add_node(child, node_index)

            return node_index


        for node in self.tree.nodes:
            add_node(node)

        for mat in materials.materials:
            res = CdaeV31.Material()
            self.cdae.materials.append(res)
            if mat is None:
                res.name = "undefined"
            else:
                res.name = mat.name

        lod = CdaeV31.Detail()
        lod.nameIndex = cdae.get_name_index("detail2")
        lod.size = 2
        lod.maxError = -1

        sub = CdaeV31.SubShape()
        sub.numNodes = len(flat_tree.nodes)
        sub.numObjects = len(flat_tree.objects)

        self.cdae.defaultRotations.pack_list(defaultRotations)
        self.cdae.defaultTranslations.pack_list(defaultTranslations)

        states = [CdaeV31.ObjectState() for _ in flat_tree.objects]
        self.cdae.pack_states(states)

        # Convert flat_nodes and flat_objects into PackedVectors
        self.cdae.pack_tree(flat_tree)
        self.cdae.pack_subshapes([sub])
        self.cdae.pack_details([lod])
        self.cdae.meshes = flat_meshes

        self.materials = materials.materials