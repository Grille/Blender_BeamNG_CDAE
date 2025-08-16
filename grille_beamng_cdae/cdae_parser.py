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


    def build_debug_info(self, cdae: CdaeV31, scene: Scene):

        def add_info(obj, dict: dict = None):
            if dict is None: return
            for key, value in dict.items():
                try:
                    obj[key] = value
                except:
                    print(key)


        def new_obj(name: str, parent = None, info: dict[str, any] = None):
            obj: bpy.types.Object = bpy.data.objects.new(name, None)
            bpy.context.collection.objects.link(obj)
            if parent is not None:
                obj.parent = parent
            add_info(obj, info)
            return obj


        for idx, obj in enumerate(scene.nodes):
            info = {
                "cdae_index": idx,
            }
            add_info(obj.object, info)

        for idx, obj in enumerate(scene.objects):
            info = {
                "cdae_index": idx,
            }
            add_info(obj.object, info)

        for idx, obj in enumerate(scene.meshes):
            info = {
                "cdae_index": idx,
                "num_frames": obj.info.numFrames,
                "num_frames_mat": obj.info.numMatFrames,
                "vertsPerFrame": obj.info.vertsPerFrame,
                "flags": obj.info.flags
            }
            add_info(obj.object, info)
        
        debug_obj = new_obj(f"cdae_debug")

        subshapes = list(cdae.unpack_subshapes())
        subshapes_obj = new_obj(f"subshapes[{len(subshapes)}]", debug_obj)
        for subshape in subshapes:
            info = {
                "nodes_first": subshape.firstNode,
                "nodes_count": subshape.numNodes,
                "objects_first": subshape.firstObject,
                "objects_count": subshape.numObjects,
            }
            new_obj(f"subshape", subshapes_obj, info)

        details = cdae.unpack_details()
        details_obj = new_obj(f"details[{len(details)}]", debug_obj)
        for detail in details:
            info = {
                "polyCount": detail.polyCount,
                "objectDetailNum": detail.objectDetailNum,
                "size": detail.size,
                "subShapeNum": detail.subShapeNum,
                "averageError": detail.averageError,
                "maxError": detail.maxError,
                "bbDetailLevel": detail.bbDetailLevel,
            }
            new_obj(f"lod:{cdae.names[detail.nameIndex]}", details_obj, detail.asdict())

        sequences = cdae.sequences
        sequences_obj = new_obj(f"seq[{len(sequences)}]", debug_obj)
        for seq in sequences:
            info = {
                "duration": seq.duration,
                "numKeyframes": seq.numKeyframes,
                "numTriggers": seq.numTriggers,
                "firstGroundFrame": seq.firstGroundFrame,
                "numGroundFrames": seq.numGroundFrames,
                "baseScale": seq.baseScale,
                "baseObjectState": seq.baseObjectState,
                "baseTranslation": seq.baseTranslation,
                "priority": seq.priority,
                "toolBegin": seq.toolBegin,
                "rotationMatters.len": len(seq.rotationMatters),
                "translationMatters.len": len(seq.translationMatters),
                "scaleMatters.len": len(seq.scaleMatters),
                "visMatters.len": len(seq.visMatters),
                "frameMatters.len": len(seq.frameMatters),
                "matFrameMatters.len": len(seq.matFrameMatters),
            }
            new_obj(f"seq:{cdae.names[seq.nameIndex]}", sequences_obj, info)

        triggers = cdae.unpack_triggers()
        triggers_obj = new_obj(f"triggers[{len(triggers)}]", debug_obj)
        for idx, trigger in enumerate(triggers):
            info = {
                "pos": trigger.pos,
                "state": trigger.state,
            }
            new_obj(f"trigger[{idx}]:", triggers_obj, info)

        states = cdae.unpack_states()
        states_obj = new_obj(f"states[{len(states)}]", debug_obj)
        for idx, state in enumerate(states):
            info = {
                "vis": state.vis,
                "frame_idx": state.frameIndex,
                "mat_frame_idx": state.matFrameIndex,
            }
            new_obj(f"state[{idx}]:", states_obj, info)

        materials = cdae.materials
        materials_obj = new_obj(f"materials[{len(materials)}]", debug_obj)
        for mat in materials:
            info = {
                "flags": mat.flags,
                "reflect": mat.reflect,
                "bump": mat.bump,
                "detail": mat.detail,
                "detailScale": mat.detailScale,
                "reflectAmount": mat.reflectionAmount,
            }
            new_obj(f"mat[{mat.name}]", materials_obj, info)

        info = {
            "bounds": f"{cdae.bounds}",
            "center": f"{cdae.center}",
            "radius": f"{cdae.radius}",
            "tube_radius": f"{cdae.tube_radius}",
            "smallest_visible_size": f"{cdae.smallest_visible_size}",
            "smallest_visible_dl": f"{cdae.smallest_visible_dl}",
            "nodeRotations.count": cdae.nodeRotations.element_count,
            "nodeTranslations.count": cdae.nodeTranslations.element_count,
            "groundRotations.count": cdae.groundRotations.element_count,
            "groundTranslations.count": cdae.groundTranslations.element_count,
        }
        new_obj("misc", debug_obj, info)



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

        if self.debug:
            self.build_debug_info(cdae, scene)

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
