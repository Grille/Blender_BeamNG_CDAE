import bpy
import numpy as np

from dataclasses import dataclass

from .numerics import *
from .cdae_v31 import CdaeV31


class CdaeParser:

    class Scene:

        @dataclass
        class Node:
            info: CdaeV31.Node
            object: bpy.types.Object


        @dataclass
        class Object:
            info: CdaeV31.Object
            object: bpy.types.Object


        @dataclass
        class Mesh:
            info: CdaeV31.Mesh
            object: bpy.types.Object
            mesh: bpy.types.Mesh


        @dataclass
        class Material:
            info: CdaeV31.Material
            material: bpy.types.Material


        def __init__(self):
            self.nodes: list[CdaeParser.Scene.Node] = []
            self.objects: list[CdaeParser.Scene.Object] = []
            self.meshes: list[CdaeParser.Scene.Mesh] = []
            self.materials: list[CdaeParser.Scene.Material] = []


        def build_scene(self, cdae: CdaeV31):
            
            for cdae_node in cdae.unpack_nodes():
                name = cdae.names[cdae_node.nameIndex]
                obj = bpy.data.objects.new(f"node:{name}", None)
                bpy.context.collection.objects.link(obj)
                self.nodes.append(CdaeParser.Scene.Node(cdae_node, obj))

            for cdae_obj in cdae.unpack_objects():
                name = cdae.names[cdae_obj.nameIndex]
                obj = bpy.data.objects.new(f"obj:{name}", None)
                bpy.context.collection.objects.link(obj)
                self.objects.append(CdaeParser.Scene.Object(cdae_obj, obj))

            for cdae_mesh in cdae.meshes:
                mesh = bpy.data.meshes.new("mesh")
                obj = bpy.data.objects.new("mesh", mesh)
                bpy.context.collection.objects.link(obj)
                self.meshes.append(CdaeParser.Scene.Mesh(cdae_mesh, obj, mesh))

            for node_info in self.nodes:
                if node_info.info.parentIndex >= 0:
                    node_info.object.parent = self.nodes[node_info.info.parentIndex].object

                if (node_info.info.firstObject >= 0):
                    obj_info = self.objects[node_info.info.firstObject]
                    obj_info.object.parent = node_info.object

            for obj_info in self.objects:
                for i in range(obj_info.info.numMeshes):
                    mesh_info = self.meshes[i + obj_info.info.startMeshIndex]
                    mesh_info.object.parent = obj_info.object

            for cdae_mat in cdae.materials:
                mat = bpy.data.materials.get(cdae_mat.name)
                if mat is None:
                    mat = bpy.data.materials.new(name=cdae_mat.name)
                self.materials.append(CdaeParser.Scene.Material(cdae_mat, mat))
            


    def __init__(self):
        self.validate = True
        self.debug = False


    def parse(self, cdae: CdaeV31):
        scene = CdaeParser.Scene()
        scene.build_scene(cdae)

        positions = cdae.defaultTranslations.unpack_list(Vec3F)
        rotations = cdae.defaultRotations.unpack_list(Quat4I16)

        for index, node_info in enumerate(scene.nodes):
            obj = node_info.object
            obj.location = positions[index].tuple3
            obj.rotation_mode = 'QUATERNION'
            obj.rotation_quaternion = rotations[index].to_blender_quaternion()

        for mesh_info in scene.meshes:
            self.build_mesh(mesh_info.info, mesh_info.mesh)
            self.add_materials(mesh_info.info, mesh_info.mesh, scene)


    def add_materials(self, info: CdaeV31.Mesh, mesh: bpy.types.Mesh, scene: Scene):
        
        for mat_info in scene.materials:
            mesh.materials.append(mat_info.material)


    def get_clean_data(self, info: CdaeV31.Mesh):

        all_indices = info.indices.to_numpy_array(np.int32).reshape(-1, 3)
        positions = info.verts.to_numpy_array(np.float32).reshape(-1, 3)

        # Collect filtered triangles and material mapping
        region_triangles = []
        region_materials = []

        for region in info.unpack_regions():
            tris = all_indices[region.get_polygon_range()]

            # Filter out triangles where any two vertices share the same position
            p0 = positions[tris[:, 0]]
            p1 = positions[tris[:, 1]]
            p2 = positions[tris[:, 2]]
            mask = ~((np.all(p0 == p1, axis=1)) | (np.all(p1 == p2, axis=1)) | (np.all(p0 == p2, axis=1)))
            tris = tris[mask]

            region_triangles.append(tris)
            region_materials.extend([region.material] * len(tris))

        indices = np.vstack(region_triangles).ravel()
        return (positions, indices, region_materials)
    

    def build_mesh(self, info: CdaeV31.Mesh, mesh: bpy.types.Mesh):

        if (info.type != CdaeV31.MeshType.STANDARD):
            return
        
        positions, indices, mat_indices = self.get_clean_data(info)

        loop_count = len(indices)
        face_count = loop_count // 3

        loop_positions = positions[indices]
        vert_positions, vert_indices = np.unique(loop_positions, axis=0, return_inverse=True)
        vert_count = vert_positions.shape[0]

        loop_start = np.arange(face_count, dtype=np.int32) * 3
        loop_total = np.full(face_count, 3, dtype=np.int32)

        mesh.vertices.add(vert_count)
        mesh.loops.add(loop_count)
        mesh.polygons.add(face_count)

        mesh.vertices.foreach_set("co", vert_positions.ravel())
        mesh.loops.foreach_set("vertex_index", vert_indices)
        mesh.polygons.foreach_set("loop_start", loop_start)
        mesh.polygons.foreach_set("loop_total", loop_total)
        mesh.update(calc_edges=True)

        mesh.polygons.foreach_set("material_index", np.array(mat_indices, dtype=np.int32))

        if info.tverts0.element_count:
            loop_tverts = info.tverts0.to_numpy_array(np.float32).reshape(-1, 2)[indices]
            layer = mesh.uv_layers.new(name="UV0")
            layer.data.foreach_set("uv", loop_tverts.ravel())

        if info.tverts1.element_count:
            loop_tverts = info.tverts1.to_numpy_array(np.float32).reshape(-1, 2)[indices]
            layer = mesh.uv_layers.new(name="UV1")
            layer.data.foreach_set("uv", loop_tverts.ravel())

        if info.colors.element_count:
            loop_colors = info.colors.to_numpy_array(np.ubyte).reshape(-1, 4)[indices].astype(np.float32) / 255
            layer = mesh.color_attributes.new(name="Color", domain='CORNER', type='FLOAT_COLOR')
            layer.data.foreach_set("color", loop_colors.ravel())

        if info.norms.element_count:
            loop_normals = -info.norms.to_numpy_array(np.float32).reshape(-1, 3)[indices]
            mesh.normals_split_custom_set(loop_normals)

        if self.validate:
            mesh.validate(verbose=self.debug)

        mesh.update()
