from grille_cdae.common import *
import bmesh
import math

from collections import defaultdict

from .v31 import *
from ...blender.object_properties import ObjectProperties
from .builder_tree import CdaeTree
from ..u8_normal_table import U8NormalTable



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

StrEnumMetaData.description[MeshDataEvalMode.Depsgraph] = "More efficient alternative to Viewport."



type _ArrayAny = np.typing.NDArray[np.generic]
type _ArrayF32 = np.typing.NDArray[np.float32]
type _ArrayI32 = np.typing.NDArray[np.int32]
type _ArrayInt = np.typing.NDArray[np.integer[Any]]
type _ArrayU8 = np.typing.NDArray[np.uint8]
type Indices = np.typing.NDArray[np.int32]



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


        def select_vertices(self, order: _ArrayInt):
            """New vertex i is old vertex order[i], for every vertex attribute."""
            if self.positions is not None:
                self.positions = self.positions[order]
            if self.normals is not None:
                self.normals = self.normals[order]
            if self.tangents is not None:
                self.tangents = self.tangents[order]
            if self.uvs0 is not None:
                self.uvs0 = self.uvs0[order]
            if self.uvs1 is not None:
                self.uvs1 = self.uvs1[order]
            if self.colors is not None:
                self.colors = self.colors[order]


        def collapse_vertices(self):
            """Tangents aren't part of the key, loop tangents of a shared vertex differ in the last bits, the first one is kept."""

            combined = self.concatenate()
            _, unique_indices, inverse = np.unique(
                combined,
                axis=0,
                return_inverse=True,
                return_index=True
            )

            self.indices = inverse.ravel()[self.indices].astype(np.int32)
            self.select_vertices(unique_indices)


        def build_draw_regions(self, regions: list[tuple[int, int]], split_blocks: bool, block_size: int = 65536):
            """
            regions: (info, triangle count) in index order.
            Torque draws with 16 bit indices relative to a block aligned to 65536 vertices, a region can't reference
            vertices from two blocks. With split_blocks, vertices get laid out block by block, a triangle that doesn't
            fit in the current block starts the next one and splits the region, vertices it shares are duplicated.
            The few vertices left at the end of a block stay unused, as in BeamNG's own conversions.
            """
            vertex_count = 0 if self.positions is None else len(self.positions)
            draw_regions: list[Tuple3I] = []

            if not split_blocks or vertex_count <= block_size:
                offset = 0
                for info, count in regions:
                    draw_regions.append((offset, count * 3, info))
                    offset += count * 3
                return draw_regions

            triangles: list[list[int]] = not_none(self.indices).reshape((-1, 3)).tolist()
            order: list[int] = []  # new vertex -> old vertex
            remap: dict[int, int] = {}  # old vertex -> new vertex, current block only
            block_end = block_size
            tri_index = 0
            for info, count in regions:
                region_start = tri_index
                for _ in range(count):
                    triangle = triangles[tri_index]
                    missing = len({v for v in triangle if v not in remap})
                    if len(order) + missing > block_end:
                        if tri_index > region_start:
                            draw_regions.append((region_start * 3, (tri_index - region_start) * 3, info))
                            region_start = tri_index
                        order.extend([order[-1]] * (block_end - len(order)))
                        block_end += block_size
                        remap.clear()
                    for k, vertex in enumerate(triangle):
                        new = remap.get(vertex)
                        if new is None:
                            new = remap[vertex] = len(order)
                            order.append(vertex)
                        triangle[k] = new
                    tri_index += 1
                if tri_index > region_start:
                    draw_regions.append((region_start * 3, (tri_index - region_start) * 3, info))

            self.indices = np.array(triangles, dtype=np.int32)
            self.select_vertices(np.array(order, dtype=np.int64))
            return draw_regions



    class BpyMeshContext:

        def __init__(self, mesh: bpy.types.Mesh):
            self.mesh = mesh


        def get_vtx_indices(self) -> Indices:
            return butils.np_new(self.mesh.loops, "vertex_index", np.int32).ravel()


        def get_vtx_data(self, key: str, size: int, indices: Indices):
            return butils.np_new(self.mesh.vertices, key, np.float32, size)[indices]


        def get_loop_data(self, key: str, size: int):
            return butils.np_new(self.mesh.loops, key, np.float32, size)
        

        def get_uv_layer(self, uv_hint: str | int):

            if isinstance(uv_hint, str):
                for item in self.mesh.uv_layers:
                    key: str = item.name
                    if uv_hint in key.lower():
                        return item.data
                return None

            if len(self.mesh.uv_layers) > uv_hint:
                return self.mesh.uv_layers[uv_hint].data

            return None
        

        def get_uv_data(self, uv_hint: str | int):

            uv_layer = self.get_uv_layer(uv_hint)
            if uv_layer is None: return None
            
            uv_data = butils.np_new(uv_layer, "uv", np.float32, 2)
            uv_data[:, 1] = 1.0 - uv_data[:, 1]
            return uv_data
            

        def get_color_data(self, indices: Indices) -> _ArrayU8 | None:

            if len(self.mesh.color_attributes) > 0:
                layer_name = self.mesh.color_attributes[0].name
            else:
                return None 
        
            color_layer = cast(bpy.types.FloatColorAttribute, self.mesh.color_attributes.get(layer_name))
            if not color_layer:
                return None

            loop_count = len(self.mesh.loops)
            vert_count = len(self.mesh.vertices)

            raw_color = butils.np_new(color_layer.data, "color", np.float32, 4)

            if color_layer.domain == 'CORNER':
                colors = raw_color.reshape((loop_count, 4))

            elif color_layer.domain == 'POINT':
                colors = raw_color.reshape((vert_count, 4))[indices]

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
        size = bounds.range()
        return math.sqrt(size.dot(size)) / 2


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

        if self.apply_scale and self.scale != Vec3F.ONE:
            scale = np.array(self.scale, dtype=np.float32)
            npmesh.positions = npmesh.positions * scale
            # normals transform with the inverse scale, skip for degenerate (zero) scale
            if np.all(scale != 0):
                normals = npmesh.normals / scale
                lengths = np.linalg.norm(normals, axis=1, keepdims=True)
                npmesh.normals = np.divide(normals, lengths, out=normals, where=lengths > 0).astype(np.float32)

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

        DrawRegion = np.dtype([
            ('elements_start', np.int32),
            ('elements_count', np.int32),
            ('material_index', np.int32),
        ])

        npmesh.collapse_vertices()
        regions = [(mat_index | CdaeV31.Mesh.DrawRegion.InfoMask.INDEXED, len(material_ranges[mat_index])) for mat_index in material_ranges]
        draw_regions = npmesh.build_draw_regions(regions, self.split_draw_regions)
        npmesh.draw_regions = np.array(draw_regions, dtype=np.int32).reshape((-1, 3))


        mesh_out = CdaeV31.Mesh()
        mesh_out.type = CdaeV31.MeshType.STANDARD

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
            mins = Vec3F(*npmesh.positions.min(axis=0).astype(float))
            maxs = Vec3F(*npmesh.positions.max(axis=0).astype(float))
            mesh_out.bounds = Box6F(mins, maxs)
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