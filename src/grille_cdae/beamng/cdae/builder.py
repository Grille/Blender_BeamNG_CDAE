from grille_cdae.common import *
import bmesh
import math

from collections import defaultdict

from .v31 import *
from ...blender.object_properties import ObjectProperties, ObjectRole
from .builder_tree import CdaeTree
from ..u8_normal_table import U8NormalTable



# pyright: reportUnknownMemberType=information



class CdaeMaterialIndexer:
    def __init__(self):
        self.material_to_index: dict[bpy.types.Material | None, int] = {}
        self.materials: list[bpy.types.Material | None] = []


    def get_index(self, bmat: bpy.types.Material | None):
        if bmat not in self.material_to_index:
            index = len(self.materials)
            self.material_to_index[bmat] = index
            self.materials.append(bmat)
        return self.material_to_index[bmat]
    

    
class MeshDataEvalMode(StrEnum):
    RawData = "None"
    ModViewport = "Viewport"
    ModRender = "Render"
    ModAll = "All"
    Depsgraph = "Depsgraph"

    def get_description(self) -> str:
        return _MeshDataEvalMode_desc.get(self, "")

_MeshDataEvalMode_desc = {
   MeshDataEvalMode.Depsgraph: "More efficient alternative to Viewport.",
}



type _ArrayAny = np.typing.NDArray[np.generic]
type _ArrayF32 = np.typing.NDArray[np.float32]
type _ArrayI32 = np.typing.NDArray[np.int32]
type _ArrayU8 = np.typing.NDArray[np.uint8]



class CdaeMeshBuilder:

    class NpMesh:

        def __init__(self):

            self.draw_regions: _ArrayI32 | None = None
            self.indices: _ArrayI32 | None = None
            self.positions: _ArrayF32 | None = None
            self.normals: _ArrayF32 | None = None
            self.tangents: _ArrayF32 | None = None
            self.uvs0: _ArrayF32 | None = None
            self.uvs1: _ArrayF32 | None = None
            self.colors: _ArrayU8 | None = None


        def concatenate(self):

            keys: list[_ArrayAny] = []
            def append(array: _ArrayAny | None):
                if array is not None:
                    keys.append(array)
            
            append(self.positions)
            append(self.normals)
            append(self.uvs0)
            append(self.uvs1)
            append(self.colors)

            return np.concatenate(keys, axis=1)
        

        def collapse_vertices(self):

            combined = self.concatenate()
            _, unique_indices, inverse = np.unique(
                combined,
                axis=0,
                return_inverse=True,
                return_index=True
            )

            self.indices = inverse[self.indices].astype(np.int32)

            if self.positions is not None:
                self.positions = self.positions[unique_indices]
            if self.normals is not None:
                self.normals = self.normals[unique_indices]
            if self.uvs0 is not None:
                self.uvs0 = self.uvs0[unique_indices]
            if self.uvs1 is not None:
                self.uvs1 = self.uvs1[unique_indices]
            if self.colors is not None:
                self.colors = self.colors[unique_indices]



    class BpyMeshContext:

        def __init__(self, mesh: bpy.types.Mesh):
            self.mesh = mesh


        def get_vtx_indices(self):
            loop_vertex_indices = np.empty(len(self.mesh.loops), dtype=np.int32)
            self.mesh.loops.foreach_get("vertex_index", loop_vertex_indices)
            return loop_vertex_indices


        def map_vtx_to_loop(self, vtx_data: _ArrayF32, size: int, indices: _ArrayI32):
            vtx_data = vtx_data.reshape((-1, size))
            return vtx_data[indices]
        

        def get_vtx_data(self, key: str, size: int, indices: _ArrayI32):
            vertex_data = np.empty(len(self.mesh.vertices) * size, dtype=np.float32)
            self.mesh.vertices.foreach_get(key, vertex_data)
            return self.map_vtx_to_loop(vertex_data, size, indices)


        def get_loop_data(self, key: str, size: int):
            loop_data = np.empty(len(self.mesh.loops) * size, dtype=np.float32)
            self.mesh.loops.foreach_get(key, loop_data)
            return loop_data.reshape((-1, size))
        

        def get_uv_layer(self, uv_hint: str | int):

            if isinstance(uv_hint, str):
                for item in self.mesh.uv_layers:
                    key: str = item.name
                    if uv_hint in key.lower():
                        return item.data
                return None

            elif isinstance(uv_hint, int):

                if len(self.mesh.uv_layers) > uv_hint:
                    return self.mesh.uv_layers[uv_hint].data

                return None

            raise TypeError(uv_hint)
        

        def get_uv_data(self, uv_hint: str | int):

            uv_layer = self.get_uv_layer(uv_hint)
            if uv_layer is None:
                return None
            
            uv_data = np.empty(len(uv_layer) * 2, dtype=np.float32)
            uv_layer.foreach_get("uv", uv_data)
            uv_data = uv_data.reshape((-1, 2))
            uv_data[:, 1] = 1.0 - uv_data[:, 1]
            return uv_data
            

        def get_color_data(self, indices: np.typing.NDArray[np.int32]):

            if len(self.mesh.color_attributes) > 0:
                layer_name = self.mesh.color_attributes[0].name
            else:
                return None 
        
            color_layer = cast(bpy.types.FloatColorAttribute, self.mesh.color_attributes.get(layer_name))
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

 

    def __init__(self, material_indexer: CdaeMaterialIndexer):
        self.apply_scale: bool = True
        self.split_draw_regions: bool = False
        self.scale = Vec3F(1,1,1)
        self.material_indexer = material_indexer
        self.use_uv_hint: bool = False
        self.uv0_hint: str = "0"
        self.uv1_hint: str = "1"
        self.compute_tangents: bool = False
        self.compute_encoded_normals: bool = False
        self.eval_mode = MeshDataEvalMode.Depsgraph
        self.depsgraph: bpy.types.Depsgraph | None = None


    @staticmethod
    def get_radius(bounds: Box6F):
        return math.sqrt(bounds.range().max_unit()*2)


    def build_from_mesh(self, mesh: bpy.types.Mesh)-> CdaeV31.Mesh:
        
        if any(len(p.vertices) > 4 for p in mesh.polygons): # pyright: ignore[reportArgumentType]
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces) # pyright: ignore[reportArgumentType]
            bm.to_mesh(mesh)
            bm.free()

        mesh.calc_loop_triangles()
        ctx = CdaeMeshBuilder.BpyMeshContext(mesh)

        vertex_indices = ctx.get_vtx_indices()

        uv0_hint = self.uv0_hint if self.use_uv_hint else 0
        uv1_hint = self.uv1_hint if self.use_uv_hint else 1

        npmesh = CdaeMeshBuilder.NpMesh()
        npmesh.positions = ctx.get_vtx_data("co", 3, vertex_indices)
        npmesh.normals = ctx.get_loop_data("normal", 3)
        npmesh.uvs0 = ctx.get_uv_data(uv0_hint)
        npmesh.uvs1 = ctx.get_uv_data(uv1_hint)
        npmesh.colors = ctx.get_color_data(vertex_indices)

        if self.compute_tangents and npmesh.uvs0 is not None and len(npmesh.uvs0) > 0:
            mesh.calc_tangents()
            npmesh.tangents = ctx.get_loop_data("tangent", 4)

        material_ranges: defaultdict[int, list[Tuple3I]] = defaultdict(list)
        for tri in mesh.loop_triangles:
            poly = mesh.polygons[tri.polygon_index]
            mat = mesh.materials[poly.material_index] if poly.material_index < len(mesh.materials) else None
            global_mat_index = self.material_indexer.get_index(mat)

            #def get_loop_index(idx: int) -> int: return tri.loops[0] # type: ignore

            loops: Tuple3I = (tri.loops[2], tri.loops[1], tri.loops[0]) # type: ignore
            material_ranges[global_mat_index].append(loops)

        
        indices_list: list[Tuple3I] = []
        for mat_index in material_ranges:
            matrange = material_ranges[mat_index]
            indices_list.extend(matrange)
        npmesh.indices = np.array(indices_list, dtype=np.int32)

        U16_LIMIT = 65535

        draw_regions: list[Tuple3I] = []
        offset = 0
        for mat_index in material_ranges:
            count = len(material_ranges[mat_index]) * 3
            info = mat_index | CdaeV31.Mesh.DrawRegion.InfoMask.INDEXED
            if self.split_draw_regions:
                while count > U16_LIMIT:
                    draw_regions.append((offset, U16_LIMIT, info))
                    offset += U16_LIMIT
                    count -= U16_LIMIT
            draw_regions.append((offset, count, info))
            offset += count

        DrawRegion = np.dtype([
            ('elements_start', np.int32),
            ('elements_count', np.int32),
            ('material_index', np.int32),
        ])
        npmesh.draw_regions = np.array(draw_regions, dtype=DrawRegion).astype(np.int32)


        mesh_out = CdaeV31.Mesh()
        mesh_out.type = CdaeV31.MeshType.STANDARD

        npmesh.collapse_vertices()
        mesh_out.draw_regions.set_array(npmesh.draw_regions)
        mesh_out.indices.set_array(npmesh.indices)
        mesh_out.verts.set_array(npmesh.positions)
        mesh_out.norms.set_array(npmesh.normals)

        if self.compute_encoded_normals:
            encoded_norms = np.zeros(len(npmesh.normals), dtype=np.uint8)
            for i in range(len(npmesh.normals)):
                encoded_norms[i] = U8NormalTable.encode_normal(npmesh.normals[i])
            mesh_out.encoded_norms.set_array(encoded_norms)

        if npmesh.tangents is not None:
            mesh_out.tangents.set_array(npmesh.tangents)

        if npmesh.uvs0 is not None:
            mesh_out.tverts0.set_array(npmesh.uvs0)
        else:
            # generate default UV so the object is visible in BeamNG (default UV values is [0.0, 1.0] as BeamNG does for a .dae without UV)
            mesh_out.tverts0.set_array(np.tile(np.array([0.0, 1.0], dtype=np.float32), (len(npmesh.positions), 1)))

        if npmesh.uvs1 is not None:
            mesh_out.tverts1.set_array(npmesh.uvs1)

        if npmesh.colors is not None:
            mesh_out.colors.set_array(npmesh.colors)


        mesh_out.numFrames = 1
        mesh_out.numMatFrames = 1
        mesh_out.vertsPerFrame = len(npmesh.positions)

        if mesh_out.vertsPerFrame > 0:
            mins = npmesh.positions.min(axis=0).astype(float)
            maxs = npmesh.positions.max(axis=0).astype(float)
            mesh_out.bounds = Box6F(*mins, *maxs)
            mesh_out.center = mesh_out.bounds.center()
            mesh_out.radius = CdaeMeshBuilder.get_radius(mesh_out.bounds)

        return mesh_out 


    def build_from_object(self, obj: bpy.types.Object | None) -> CdaeV31.Mesh:
        
        if obj is None or not ObjectProperties.has_mesh(obj):
            null = CdaeV31.Mesh()
            return null

        assert isinstance(obj.data, bpy.types.Mesh)
            
        if self.eval_mode == MeshDataEvalMode.Depsgraph:
            
            eval_obj = obj.evaluated_get(self.depsgraph)
            mesh = eval_obj.to_mesh()
            try:
                return self.build_from_mesh(mesh)
            finally: 
                eval_obj.to_mesh_clear() 

        else:

            collection = not_none(bpy.context.collection)
            view_layer = not_none(bpy.context.view_layer)

            temp_obj: bpy.types.Object = obj.copy()
            mesh = temp_obj.data = obj.data.copy()

            collection.objects.link(temp_obj)

            active = view_layer.objects.active
            view_layer.objects.active = temp_obj
            
            match self.eval_mode:
                case MeshDataEvalMode.RawData:
                    modifiers = []
                case MeshDataEvalMode.ModViewport:
                    modifiers = [mod for mod in temp_obj.modifiers if mod.show_viewport]
                case MeshDataEvalMode.ModRender:
                    modifiers = [mod for mod in temp_obj.modifiers if mod.show_render]
                case MeshDataEvalMode.ModAll:
                    modifiers = temp_obj.modifiers
                case _:
                    raise Exception(self.eval_mode)

            for mod in modifiers:
                bpy.ops.object.modifier_apply(modifier=mod.name)

            bpy.data.objects.remove(temp_obj, do_unlink=True)
            view_layer.objects.active = active

            try:
                return self.build_from_mesh(mesh)
            finally:
                bpy.data.meshes.remove(mesh)



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


    def sample(self, obj: types.Object | None):
        transforms_enabled = obj is not None and self.sample_transforms_enabled
        keyframes_enabled = obj is not None and self.sample_keyframes_enabled
        obj = cast(types.Object, obj)
        transforms = self.sample_current(obj) if transforms_enabled else Transforms()
        if keyframes_enabled:
            self.sample_keyframes(obj)
        else:
            self.nodes_enabled.append(False)
        return CdaeKeyframeSampler.Result(transforms, keyframes_enabled)



    def sample_keyframes(self, obj: bpy.types.Object):

        scene = not_none(bpy.context.scene)
        
        frame_backup = scene.frame_current

        frame_range = self.end - self.start
        frame_scale = frame_range / self.sample_count

        for iframe in (range(self.sample_count)):
            scaled_frame = iframe * frame_scale
            final_frame = scaled_frame + self.start
            self.keyframes.append(self.sample_frame(obj, scene, final_frame))

        scene.frame_set(frame_backup)

        self.nodes_enabled.append(True)


    def sample_frame(self, obj: types.Object, scene: types.Scene, frame: float) -> Transforms:
        intframe = int(frame)
        subframe = frame - intframe
        scene.frame_set(intframe, subframe=subframe)
        return self.sample_current(obj)
    

    def sample_current(self, obj: bpy.types.Object) -> Transforms:
        return Transforms.from_blender_matrix(obj.matrix_world)


class CdeaBuilder:
    
    def __init__(self):
        self.cdae = CdaeV31()
        self.tree = CdaeTree()
        self.material_indexer = CdaeMaterialIndexer()
        self.mesh_builder = CdaeMeshBuilder(self.material_indexer)
        self.sampler = CdaeKeyframeSampler()
        self.materials: list[bpy.types.Material] = []
        self.readonly: bool = False


    def build(self):

        cdae = self.cdae

        flat_tree = cdae.unpack_tree()
        flat_meshes = cdae.meshes

        if self.mesh_builder.eval_mode == MeshDataEvalMode.Depsgraph:
            self.mesh_builder.depsgraph = bpy.context.evaluated_depsgraph_get()

        def add_node(node: CdaeTree.Node, parent_index: int = -1) -> int:
            
            node_samples = self.sampler.sample(node.bpy_sample_obj)
            transforms = node_samples.transforms

            if self.mesh_builder.apply_scale:
                self.mesh_builder.scale = transforms.scale
                transforms = Transforms(transforms.translation, Vec3F.ONE, transforms.rotation)

            (node_index, flat_node) = flat_tree.create_node(node.name, parent_index, transforms)

            for obj in node.objects:
                (obj_index, flat_obj) = flat_tree.create_object(obj.name, node_index)

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
            shapeidx = shapes_dict.get(not_none(detail.shape), -1)
            detail.template.nameIndex = self.cdae.get_name_index(key)
            detail.template.subShapeNum = shapeidx
            details.append(detail.template)


        if self.sampler.sample_keyframes_enabled:
            seq = self.sampler.create_sequence()
            cdae.sequences.append(seq)
            seq.nameIndex = self.cdae.get_name_index("ambiant")

            kf_loc: list[Vec3F] = []
            kf_rot: list[Quat4I16] = []
            kf_scl: list[Vec3F] = []
            for frame in self.sampler.keyframes:
                kf_loc.append(frame.translation)
                kf_rot.append(frame.rotation)
                kf_scl.append(frame.scale)

            self.cdae.nodeTranslations.pack_list(kf_loc)
            self.cdae.nodeRotations.pack_list(kf_rot)
            self.cdae.nodeAlignedScales.pack_list(kf_scl)

        
        self.materials = []
        for mat in self.material_indexer.materials:
            res = CdaeV31.Material()
            self.cdae.materials.append(res)
            if mat is None:
                res.name = "undefined"
            else:
                res.name = mat.name
                self.materials.append(mat)


        states = [CdaeV31.ObjectState() for _ in flat_tree.objects]
        self.cdae.pack_states(states)
        self.cdae.pack_tree(flat_tree)
        self.cdae.pack_subshapes(shapes)
        self.cdae.pack_details(details)
        self.cdae.meshes = flat_meshes

        if len(flat_meshes) > 0:
            self.cdae.bounds = flat_meshes[0].bounds
            for i in range(1, len(flat_meshes)):
                self.cdae.bounds = self.cdae.bounds.extended(flat_meshes[i].bounds)
        self.cdae.center = self.cdae.bounds.center()
        self.cdae.radius = CdaeMeshBuilder.get_radius(self.cdae.bounds)
        self.cdae.tube_radius = self.cdae.radius