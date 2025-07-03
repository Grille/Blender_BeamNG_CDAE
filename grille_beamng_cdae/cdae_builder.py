import bpy
import bmesh

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

from .cdae_v31 import *


class CdaeTree:

    class Node:
        def __init__(self, name: str, nodes: 'list[CdaeTree.Node]' = [], objects: 'list[CdaeTree.Object]' = []):
            self.name = name
            self.nodes = nodes
            self.objects = objects


        def enumerate_meshes(self):
            for obj in self.objects:
                for mesh in obj.meshes:
                    yield mesh

            for node in self.nodes:
                yield from node.enumerate_meshes()


    class Object:
        def __init__(self, name: str, meshes: 'list[CdaeTree.Mesh]' = []):
            self.name = name
            self.meshes = meshes

    
    class Mesh:
        def __init__(self, obj: bpy.types.Object):
            self.bpy_obj = obj


    def __init__(self):
        self.nodes: list[CdaeTree.Node] = []


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

        for obj in root_objects:
            obj_type = CdaeTree.get_node_type(obj)
            if obj_type is not None:
                root_dict[obj_type].append(obj)

        for root in root_dict[CdaeTree.Node]:
            self.nodes.append(CdaeTree.build_node_recursive(root))

        for root in root_dict[CdaeTree.Object]:
            obj = CdaeTree.build_object(root)
            node = CdaeTree.Node(root.name, objects=[obj])
            self.nodes.append(node)

        for root in root_dict[CdaeTree.Mesh]:
            mesh = CdaeTree.Mesh(root)
            obj = CdaeTree.Object(root.name, meshes=[mesh])
            node = CdaeTree.Node(root.name, objects=[obj])
            self.nodes.append(node)

        
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



class CdeaMeshBuilder:

    @staticmethod
    def extract_mesh_data(obj: bpy.types.Object) -> CdaeV31.Mesh:
        mesh_out = CdaeV31.Mesh()

        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()

        bm = bmesh.new()
        bm.from_mesh(eval_mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        mesh_out.type = CdaeV31.MeshType.STANDARD

        # Cleanup
        bm.free()
        eval_obj.to_mesh_clear()

        return mesh_out



class CdeaBuilder:
    
    def __init__(self):
        self.cdae = CdaeV31()
        self.tree = CdaeTree()


    def build(self):
        for node in self.tree.nodes:
            self.convert_tree_to_cdaev31(node)


    def convert_tree_to_cdaev31(self, cdae_tree_root: 'CdaeTree.Node'):

        cdae = self.cdae

        flat_nodes: list[CdaeV31.Node] = []
        flat_objects: list[CdaeV31.Object] = []
        flat_meshes: list[CdaeV31.Mesh] = []

        def add_node(node: 'CdaeTree.Node', parent_index: int = -1) -> int:
            node_index = len(flat_nodes)
            flat_nodes.append(CdaeV31.Node())  # Will fill fields later
            current_node = flat_nodes[node_index]
            current_node.nameIndex = cdae.require_name_index(node.name)
            current_node.parentIndex = parent_index

            # Handle objects
            current_node.firstObject = -1
            last_object_index = -1
            for obj in node.objects:
                obj_index = len(flat_objects)
                flat_objects.append(CdaeV31.Object())
                flat_obj = flat_objects[obj_index]
                flat_obj.nameIndex = cdae.require_name_index(obj.name)
                flat_obj.numMeshes = len(obj.meshes)
                flat_obj.startMeshIndex = len(flat_meshes)
                flat_obj.nodeIndex = node_index
                flat_obj.firstDecal = -1
                flat_obj.nextSibling = -1

                for mesh in obj.meshes:
                    flat_meshes.append(CdeaMeshBuilder.extract_mesh_data(mesh.bpy_obj))  # Not a CdaeV31 class, assumed your wrapper type

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

        add_node(cdae_tree_root)

        # Convert flat_nodes and flat_objects into PackedVectors
        self.cdae.pack_nodes(flat_nodes)
        self.cdae.pack_objects(flat_objects)
        self.cdae.meshes = flat_meshes