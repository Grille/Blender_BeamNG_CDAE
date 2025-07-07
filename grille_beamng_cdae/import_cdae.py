import os
import bpy
import struct
import numpy as np

from io import BufferedReader
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty

from .cdae_v31 import CdaeV31

class ImportCdae(Operator, ImportHelper):
    bl_idname = "import_scene.beamng"
    bl_label = "Import BeamNG"
    filename_ext = ".cdae"
    filter_glob = StringProperty(default="*.cdae", options={'HIDDEN'})

    def execute(self, context):
        cdae = CdaeV31()
        cdae.read_from_file(self.filepath)

        meshes: list[tuple[CdaeV31.Mesh, bpy.types.Object, bpy.types.Mesh]] = []
        for cdae_mesh in cdae.meshes:
            mesh = bpy.data.meshes.new("mesh")
            obj = bpy.data.objects.new("mesh", mesh)
            bpy.context.collection.objects.link(obj)
            meshes.append((cdae_mesh, obj, mesh))

        objects: list[tuple[CdaeV31.Object, bpy.types.Object]] = []
        for cdae_obj in cdae.unpack_objects():
            name = cdae.names[cdae_obj.nameIndex]
            obj = bpy.data.objects.new(f"obj:{name}", None)
            bpy.context.collection.objects.link(obj)
            objects.append((cdae_obj, obj))

        nodes: list[tuple[CdaeV31.Node, bpy.types.Object]] = []
        for cdae_node in cdae.unpack_nodes():
            name = cdae.names[cdae_node.nameIndex]
            obj = bpy.data.objects.new(f"node:{name}", None)
            bpy.context.collection.objects.link(obj)
            nodes.append((cdae_node, obj))

        for node_info in nodes:
            if node_info[0].parentIndex >= 0:
                node_info[1].parent = nodes[node_info[0].parentIndex][1]

            if (node_info[0].firstObject >= 0):
                obj_info = objects[node_info[0].firstObject]
                obj_info[1].parent = node_info[1]

        for obj_info in objects:
            for i in range(obj_info[0].numMeshes):
                mesh_info = meshes[i + obj_info[0].startMeshIndex]
                mesh_info[1].parent = obj_info[1]

        for mesh_info in meshes:
            info = mesh_info[0]
            mesh = mesh_info[2]

            if (info.type != CdaeV31.MeshType.STANDARD):
                continue

            positions = info.verts.to_numpy_buffer(np.float32, 3).reshape(-1, 3)
            tverts0 = info.tverts0.to_numpy_buffer(np.float32, 2).reshape(-1, 2)
            tverts1 = info.tverts1.to_numpy_buffer(np.float32, 2).reshape(-1, 2)
            normals = info.norms.to_numpy_buffer(np.float32, 3).reshape(-1, 3)
            indices = info.indices.to_numpy_buffer(np.int32)

            vert_count = len(positions) // 3
            loop_count = len(indices)
            face_count = loop_count // 3

            print(info.norms.element_count)
            print(normals.shape)

            # Expand to loop-space
            loop_positions = positions[indices]
            if info.norms.element_count:
                loop_normals = normals[indices]

            mesh.vertices.add(loop_count)
            mesh.loops.add(loop_count)
            mesh.polygons.add(face_count)

            mesh.vertices.foreach_set("co", loop_positions.ravel())
            mesh.loops.foreach_set("vertex_index", np.arange(loop_count, dtype=np.int32))

            loop_start = np.arange(face_count, dtype=np.int32) * 3
            loop_total = np.full(face_count, 3, dtype=np.int32)
            mesh.polygons.foreach_set("loop_start", loop_start)
            mesh.polygons.foreach_set("loop_total", loop_total)
        
            mesh.validate()

            if info.norms.element_count:
                mesh.normals_split_custom_set(loop_normals)

            mesh.update()


        

        return {'FINISHED'}
        
    