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
    

    def parse_node_path(self, path: str):
        split_path = re.split(r'[\\/\.]', path)
        if len(split_path) == 0:
            raise Exception("no path")
        return split_path


    def get_node_by_path(self, path: str) -> 'CdaeTree.Node':

        split_path = self.parse_node_path(path)
        
        node = self
        for key in split_path:
            node = node.get_child_node(key)

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



class CdaeTreeBuildMode(str, Enum):
    NONE = "NONE"
    SINGLE_SHAPE = "SINGLE_SHAPE"
    DAE_NODE_TREE = "DAE_NODE_TREE"
    FLAT_DUMP = "FLAT_DUMP"
    BLENDER_HIERACHY = "BLENDER_HIERACHY"



class TempTreeNode:

    def __init__(self, obj: bpy.types.Object):
        self.obj = obj
        self.children: list[TempTreeNode] = []



class CdaeTree:

    class Mesh:
        def __init__(self, obj: bpy.types.Object):
            self.bpy_mesh_obj = obj



    class Object:

        def __init__(self, name: str):
            self.name = name
            self.meshes: list[CdaeTree.Mesh] = []


        def set_mesh(self, index: int, obj: bpy.types.Object):
            
            if len(self.meshes) > index:
                if self.meshes[index].bpy_mesh_obj is None:
                    self.meshes[index].bpy_mesh_obj = obj
                else:
                    raise Exception()
            
            while len(self.meshes) < index:
                self.meshes.append(CdaeTree.Mesh(None))
            
            self.meshes.append(CdaeTree.Mesh(obj))
    


    class Node(CdaeNodeList):

        def __init__(self, name: str, nodes: 'list[CdaeTree.Node]', objects: 'list[CdaeTree.Object]'):

            super().__init__(nodes)
            self.bpy_sample_obj: bpy.types.Object = None
            self.name = name
            self.objects = objects
            self.transfroms: Transforms = Transforms()
            self.keyframes: list[Transforms] = []


        def get_object(self, name: str = None):
            if name is None:
                name = self.name
            for obj in self.objects:
                if obj.name == name:
                    return obj
            obj = CdaeTree.Object(name)
            self.objects.append(obj)
            return obj
        

        def iter_meshes(self):

            for obj in self.objects:
                for mesh in obj.meshes:
                    yield mesh

            for node in self.nodes:
                yield from node.iter_meshes()



    class SubShape(CdaeNodeList):
        
        def __init__(self):
            super().__init__([])


        def iter_meshes(self):
            for node in self.nodes:
                yield from node.iter_meshes()


    
    class Detail:

        def __init__(self, shape: 'CdaeTree.SubShape' = None, mesh_index: int = 0):
            self.shape = shape
            self.template = CdaeV31.Detail()
            self.template.objectDetailNum = mesh_index



    def __init__(self):
        self.shapes: dict[str, CdaeTree.SubShape] = {}
        self.details: dict[str, CdaeTree.Detail] = {}
        self.build_mode = CdaeTreeBuildMode.NONE
        self._mesh_index_counter = 0


    def get_shape(self, name: str = "_default_") -> SubShape:
        shape = self.shapes.get(name, None)
        if shape is None:
            shape = CdaeTree.SubShape()
            self.shapes[name] = shape
        return shape
    

    def _get_obj_name(self, obj: bpy.types.Object) -> str:
        name: str = obj.name
        return name.replace(".", "_")
    

    def iter_meshes(self):
        for shape in self.shapes.values():
            yield from shape.iter_meshes()


    def _add_obj_FLAT_DUMP(self, obj: bpy.types.Object):

        if not ObjectProperties.has_mesh(obj):
            return

        shape = self.get_shape()
        node = shape.get_child_node(self._get_obj_name(obj))
        node.bpy_sample_obj = obj
        node.get_object().set_mesh(0, obj)


    def _add_obj_DAE_NODE_TREE(self, obj: bpy.types.Object):

        shape = self.get_shape()
        has_mesh = ObjectProperties.has_mesh(obj)
        lod_size = ObjectProperties.get_lod(obj)
        namespace = "base00.start01"

        def add(path: str, use_obj = True):
            node = shape.get_node_by_path(path)
            if use_obj:
                node.bpy_sample_obj = obj
                node.get_object().set_mesh(0, obj)

        match ObjectProperties.get_role(obj):
            case ObjectRole.Generic:
                path = getattr(obj, ObjectProperties.PATH)
                add(path, has_mesh)
            case ObjectRole.Mesh:
                add(f"{namespace}.detail{lod_size}")
            case ObjectRole.Collision:
                add(f"{namespace}.colmesh-1")
            case ObjectRole.Billboard:
                bb = "bbz" if getattr(obj, ObjectProperties.BB_FLAG0) else "bb"
                add(f"{namespace}.{bb}_billboard{lod_size}")
            case ObjectRole.NullDetail:
                add(f"{namespace}.nulldetail{lod_size}", False)
            case ObjectRole.AutoBillboard:
                add(f"{namespace}.bb_autobillboard{lod_size}", False)
                self.details["bb_autobillboard"] = detail = CdaeTree.Detail(shape, -1)
                detail.template.bbDimension = getattr(obj, ObjectProperties.BB_DIMENSION)
                detail.template.bbEquatorSteps = getattr(obj, ObjectProperties.BB_EQUATOR_STEPS)
                detail.template.size = lod_size
            case _:
                raise ValueError()


    def add_object(self, obj: bpy.types.Object):

        match self.build_mode:
            case CdaeTreeBuildMode.NONE:
                return
            case CdaeTreeBuildMode.FLAT_DUMP:
                self._add_obj_FLAT_DUMP(obj)
            case CdaeTreeBuildMode.DAE_NODE_TREE:
                self._add_obj_DAE_NODE_TREE(obj)
            case _:
                raise ValueError()
            
        return
    

    def _add_objs_BLENDER_HIERACHY(self, objects: set[bpy.types.Object]):

        tnodes: dict[bpy.types.Object, TempTreeNode] = {}
        
        for obj in objects:
            tnodes[obj] = TempTreeNode(obj)
        
        roots: list[TempTreeNode] = []
        for obj, tnode in tnodes.items():
            parent = obj.parent
            if parent and parent in objects:
                parent_node = tnodes[parent]
                parent_node.children.append(tnode)
            else:
                roots.append(tnode)
        
        shape = self.get_shape()
        def add(tnode: TempTreeNode, path: str):
            print(f"get {path}")
            node = shape.get_node_by_path(path)
            if ObjectProperties.has_mesh(tnode.obj):
                node.bpy_sample_obj = obj
                node.get_object().set_mesh(0, tnode.obj)
            for child in tnode.children:
                add(child, f"{path}.{self._get_obj_name(child.obj)}")

        for tnode in roots:
            add(tnode, self._get_obj_name(tnode.obj))


    def add_objects(self, objects: set[bpy.types.Object]):
        match self.build_mode:
            case CdaeTreeBuildMode.BLENDER_HIERACHY:
                self._add_objs_BLENDER_HIERACHY(objects)
            case _:
                for obj in objects: self.add_object(obj)


    def add_lock_tocken(self):
        pass


    @staticmethod
    def from_objects(objects: set[bpy.types.Object]) -> 'CdaeTree':
        tree = CdaeTree()
        tree.add_objects(objects)
        return tree
    

    @staticmethod
    def from_selection() -> 'CdaeTree':
        selected = set(bpy.context.selected_objects)
        return CdaeTree.from_objects(selected)


