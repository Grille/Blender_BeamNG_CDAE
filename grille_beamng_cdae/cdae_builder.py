import bpy
import re
import numpy as np

from numpy.typing import NDArray
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from .cdae_v31 import *


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
            self.name = name
            self.objects = objects


        def enumerate_meshes(self):
            for obj in self.objects:
                for mesh in obj.meshes:
                    yield mesh

            for node in self.nodes:
                yield from node.enumerate_meshes()


    class Object:
        def __init__(self, name: str, meshes: 'list[CdaeTree.Mesh]'):
            self.name = name
            self.meshes = meshes

    
    class Mesh:
        def __init__(self, obj: bpy.types.Object):
            self.bpy_obj = obj


    def __init__(self):
        super().__init__([])


    def enumerate_meshes(self):
        for node in self.nodes:
            yield from node.enumerate_meshes()


    @staticmethod
    def get_node_type(bpy_obj: bpy.types.Object) -> type:
        if bpy_obj.type == 'EMPTY':
            has_mesh_child = any(child.type == 'MESH' for child in bpy_obj.children)
            return CdaeTree.Object if has_mesh_child else CdaeTree.Node
        elif bpy_obj.type == 'MESH':
            return CdaeTree.Mesh
        else:
            return None


    def add_objects(self, objects: set[bpy.types.Object]):

        root_objects = [obj for obj in objects if obj.parent not in objects or obj.parent is None]
        root_dict: dict[type, list[bpy.types.Object]] = {
            CdaeTree.Node: [],
            CdaeTree.Object: [],
            CdaeTree.Mesh: [],
        }

        CDAE_PATH = "cdae_path"
        path_objects: set[bpy.types.Object] = set()

        for obj in root_objects:
            if CDAE_PATH in obj:
                path_objects.add(obj)
            else:
                obj_type = CdaeTree.get_node_type(obj)
                if obj_type is not None:
                    root_dict[obj_type].append(obj)


        for root in root_dict[CdaeTree.Node]:
            self.nodes.append(CdaeTree.build_node_recursive(root))

        for root in root_dict[CdaeTree.Object]:
            obj = CdaeTree.build_object(root)
            node = CdaeTree.Node(root.name, [], [obj])
            self.nodes.append(node)

        for root in root_dict[CdaeTree.Mesh]:
            mesh = CdaeTree.Mesh(root)
            obj = CdaeTree.Object(root.name, [mesh])
            node = CdaeTree.Node(root.name, [], [obj])
            self.nodes.append(node)
            

        for obj in path_objects:
            path: str = obj[CDAE_PATH]
            self.add_object_by_path(obj, path)


    def get_path_node(self, path: str) -> 'CdaeTree.Node':

        split_path = re.split(r'[\\/\.]', path)
        if len(split_path) == 0:
            raise Exception("no path")
        
        node = self.get_child_node(split_path[0])
        for key in split_path[1:]:
            node = node.get_child_node(key)

        return node


    def add_object_by_path(self, obj: bpy.types.Object, path: str):

        obj_type = CdaeTree.get_node_type(obj)
        if obj_type is None:
            return
        
        parent = self.get_path_node(path)
        name = parent.name

        if obj_type is CdaeTree.Object:
            cdae_obj = CdaeTree.build_object(obj)
            cdae_obj.name = name
            parent.objects.append(cdae_obj)

        if obj_type is CdaeTree.Mesh:
            cdae_mesh = CdaeTree.Mesh(obj)
            cdae_obj = CdaeTree.Object(name, meshes=[cdae_mesh])
            parent.objects.append(cdae_obj)


    @staticmethod
    def from_objects(objects: set[bpy.types.Object]) -> 'CdaeTree':
        tree = CdaeTree()
        tree.add_objects(objects)
        return tree
    

    @staticmethod
    def from_selection() -> 'CdaeTree':
        selected = set(bpy.context.selected_objects)
        return CdaeTree.from_objects(selected)


    @staticmethod
    def build_object(bpy_obj: bpy.types.Object) -> 'CdaeTree.Object':
        obj = CdaeTree.Object(bpy_obj.name)

        for mesh_obj in bpy_obj.children:
            if CdaeTree.get_node_type(mesh_obj) == CdaeTree.Mesh:
                mesh = CdaeTree.Mesh(mesh_obj)
                obj.meshes.append(mesh)


    @staticmethod
    def build_node_recursive(bpy_obj: bpy.types.Object) -> 'CdaeTree.Node':
        node = CdaeTree.Node(bpy_obj.name)

        for child in bpy_obj.children:

            type = CdaeTree.get_node_type(child)

            if type == CdaeTree.Object:
                node.objects.append(CdaeTree.build_object(child))

            elif type == CdaeTree.Node:
                node.nodes.append(CdaeTree.build_node_recursive(child))

        return node


class CdaeMaterialIndexer:
    def __init__(self):
        self.material_to_index = {}
        self.materials: list[bpy.types.Material] = []

    def get_index(self, mat: bpy.types.Material):
        if mat not in self.material_to_index:
            index = len(self.materials)
            self.material_to_index[mat] = index
            self.materials.append(mat)
        return self.material_to_index[mat]
    
    
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

        # Clamp and convert to uint8
        colors = np.clip(colors, 0.0, 1.0)
        colors_u8 = (colors * 255.0 + 0.5).astype(np.uint8)

        # Pack into uint32: 0xRRGGBBAA
        packed = (
            (colors_u8[:, 0].astype(np.uint32) << 24) |
            (colors_u8[:, 1].astype(np.uint32) << 16) |
            (colors_u8[:, 2].astype(np.uint32) << 8)  |
            (colors_u8[:, 3].astype(np.uint32))
        )

        return packed
        

    def build_from_mesh(self, mesh: bpy.types.Mesh, material_indexer: CdaeMaterialIndexer)-> CdaeV31.Mesh:
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

        # Build index buffer: each triangle uses three consecutive loop vertices
        # mesh.loop_triangles contains tuples of loop indices, which map 1:1 to positions/normals
        indices = np.empty((len(mesh.loop_triangles), 3), dtype=np.int32)
        for i, tri in enumerate(mesh.loop_triangles):
            indices[i, 0] = tri.loops[0]
            indices[i, 1] = tri.loops[1]
            indices[i, 2] = tri.loops[2]

        material_to_ranges = defaultdict(list)
        for i, tri in enumerate(mesh.loop_triangles):
            poly = mesh.polygons[tri.polygon_index]
            mat = mesh.materials[poly.material_index] if poly.material_index < len(mesh.materials) else None
            global_mat_index = material_indexer.get_index(mat)
            material_to_ranges[global_mat_index].append(i)

        # sort globally consistent material indices
        material_indices = sorted(material_to_ranges.keys())
        draw_regions = []
        offset = 0
        for mat_index in material_indices:
            count = len(material_to_ranges[mat_index])
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

        return mesh_out


    def build_from_object(self, obj: bpy.types.Object, material_indexer: CdaeMaterialIndexer)-> CdaeV31.Mesh:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj: bpy.types.Object = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        try:
            return self.build_from_mesh(mesh, material_indexer)
        finally:
            eval_obj.to_mesh_clear()



class CdeaBuilder:
    
    def __init__(self):
        self.cdae = CdaeV31()
        self.tree = CdaeTree()


    def build(self):

        cdae = self.cdae

        flat_nodes: list[CdaeV31.Node] = []
        flat_objects: list[CdaeV31.Object] = []
        flat_meshes: list[CdaeV31.Mesh] = []

        materials = CdaeMaterialIndexer()

        def add_node(node: 'CdaeTree.Node', parent_index: int = -1) -> int:
            print(f"add_node {node.name}")
            node_index = len(flat_nodes)
            flat_nodes.append(CdaeV31.Node())  # Will fill fields later
            current_node = flat_nodes[node_index]
            current_node.nameIndex = cdae.get_name_index(node.name)
            current_node.parentIndex = parent_index

            # Handle objects
            current_node.firstObject = -1
            last_object_index = -1
            for obj in node.objects:
                obj_index = len(flat_objects)
                flat_objects.append(CdaeV31.Object())
                flat_obj = flat_objects[obj_index]
                flat_obj.nameIndex = cdae.get_name_index(obj.name)
                flat_obj.numMeshes = len(obj.meshes)
                flat_obj.startMeshIndex = len(flat_meshes)
                flat_obj.nodeIndex = node_index
                flat_obj.firstDecal = -1
                flat_obj.nextSibling = -1

                for mesh in obj.meshes:
                    mesh_builder = CdeaMeshBuilder()
                    flat_meshes.append(mesh_builder.build_from_object(mesh.bpy_obj, materials))

                if current_node.firstObject == -1:
                    current_node.firstObject = obj_index
                if last_object_index != -1:
                    flat_objects[last_object_index].nextSibling = obj_index
                last_object_index = obj_index

            # Handle children
            current_node.firstChild = -1
            current_node.nextSibling = -1

            last_child_index = -1
            for child in node.nodes:
                child_index = add_node(child, node_index)
                if current_node.firstChild == -1:
                    current_node.firstChild = child_index
                if last_child_index != -1:
                    flat_nodes[last_child_index].nextSibling = child_index
                last_child_index = child_index

            return node_index

        for node in self.tree.nodes:
            add_node (node)

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
        sub.numNodes = len(flat_nodes)
        sub.numObjects = len(flat_objects)


        self.cdae.defaultRotations.alloc(len(flat_nodes))
        self.cdae.defaultTranslations.alloc(len(flat_nodes))

        # Convert flat_nodes and flat_objects into PackedVectors
        self.cdae.pack_nodes(flat_nodes)
        self.cdae.pack_objects(flat_objects)
        self.cdae.pack_subshapes([sub])
        self.cdae.pack_details([lod])
        self.cdae.meshes = flat_meshes