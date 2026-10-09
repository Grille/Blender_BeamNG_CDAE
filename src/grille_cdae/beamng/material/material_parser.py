from __future__ import annotations

from dataclasses import field as dataclass_field, replace as dataclass_replace

from grille_cdae.common import *
from grille_cdae.enums import *

from ...blender.material_properties import MaterialProperties
from ...blender.shader_nodes import BeamMaterial, BeamBDSF10Basic, BeamImageTex, BeamRGBA, BeamStageMix, BeamUVData, BeamUVAnimation, ReflectionMode
from ...blender.shader_node_builder import NodeTreeBuilder
from .material import *
from .material_builder import MaterialBuilder, MaterialExportError, MAX_STAGES
from .node_fields import Field, Tex, Value, STAGE_FIELDS, STAGE_NODE, MATERIAL_FIELDS, UV_ANIMATION, INVERSE, from_srgb



class MaterialImportError(Exception):
    """The material can't be imported at all."""



@dataclass
class _Context:
    """State while creating the nodes of one stage."""
    tree: bpy.types.ShaderNodeTree
    stage: MaterialStage
    location: str
    detail: bool = False
    # created on demand, shared by all maps of the stage
    shared: dict[str, bpy.types.Node] = dataclass_field(default_factory=dict[str, bpy.types.Node])

    @property
    def animated(self) -> bool:
        return self.stage.animation.flags != AnimationFlags.NONE



_TEX_KEYS = ("map", "uv", "value", "instance", "vertex")


def _resolve(root: object, path: str) -> tuple[Any, str]:
    *parents, name = path.split(".")
    for parent in parents: root = getattr(root, parent)
    return root, name


def _get_field(socket: TextureSocket, key: str) -> Any:
    try:
        return socket.get_field(key)
    except KeyError:
        return None


def _set_socket(node: bpy.types.Node, name: str, value: object):
    butils.set_default_value(node.inputs[name], cast(SocketValue, value))


def _is_bundle(socket: bpy.types.NodeSocket) -> bool:
    return socket.type == 'BUNDLE'



class MaterialParser:
    """Creates a node tree made of the addon's shader nodes from a BeamNG material, using the same field tables as the export."""

    def __init__(self, target_version = MaterialVersion.V1_5, base_dir: str | None = None):
        self.target_version = target_version
        self.force_alpha_clip = False
        self.base_dir = base_dir
        self.issues: list[str] = []


    def convert_bmat(self, bmat: bpy.types.Material, force_conversion: bool = True):

        builder = MaterialBuilder(MaterialVersion.NONE)
        try:
            mat = builder.build_from_bmat(bmat)
        except MaterialExportError:
            mat = builder.material # not a BeamNG node tree (yet)

        if (mat.version == MaterialVersion.NONE or force_conversion):
            if mat.version == MaterialVersion.NONE: mat.version = self.target_version
            self.parse_to_bmat(mat, bmat)


    def _issue(self, location: str, message: str):
        self.issues.append(f"[{location}]: {message}")


    def parse_to_bmat(self, src: Material, dst: bpy.types.Material):

        try:
            # BeamNG treats materials without version as 1.0
            version = src.version if src.is_set("version") else MaterialVersion.V1
        except ValueError:
            raise MaterialImportError(f"Unknown material version '{src['version']}'.")
        stage_node = STAGE_NODE.get(version)
        if stage_node is None:
            raise MaterialImportError(f"Material version {float(version)} is not supported.")

        tree = not_none(dst.node_tree)
        builder = NodeTreeBuilder(tree)
        builder.clear()

        MaterialProperties.set_ground_type(dst, src.ground_type)

        output = tree.nodes.new(NodeName.OutputMaterial)
        mat_node = cast(BeamMaterial, tree.nodes.new(BeamMaterial.bl_idname))
        tree.links.new(mat_node.outputs[SocketName.Shader], output.inputs[SocketName.Surface])
        self._import_material(src, mat_node)

        stage_count = min(max(src.active_layers, 1), MAX_STAGES)
        shader = self._import_stage(tree, stage_node, src.stages[0], 0)
        for index in range(1, stage_count):
            mix = tree.nodes.new(BeamStageMix.bl_idname)
            tree.links.new(shader.outputs[0], mix.inputs[BeamStageMix.Sockets.BASE])
            tree.links.new(self._import_stage(tree, stage_node, src.stages[index], index).outputs[0], mix.inputs[BeamStageMix.Sockets.OVERLAY])
            shader = mix

        tree.links.new(shader.outputs[0], mat_node.inputs[SocketName.BNGShader])
        builder.arrange_nodes(300, 150)


    def _import_material(self, src: Material, node: BeamMaterial):

        LS = BeamMaterial.Sockets
        # always set, the model defaults are BeamNG's file defaults while some node defaults differ (e.g. invert backface normals)
        for field in MATERIAL_FIELDS:
            if isinstance(field, Value):
                _set_socket(node, field.socket, INVERSE[field.conv](getattr(src, field.path)))

        if src.alpha_test:
            _set_socket(node, LS.CLIP_T, src.alpha_ref / 255)
        if src.subsurface.enabled:
            _set_socket(node, LS.SUBSURFACE_SCATTERING, src.subsurface.intensity)

        if self.force_alpha_clip:
            _set_socket(node, LS.CLIP, True)
            _set_socket(node, LS.CLIP_T, 0.5)

        if src.translucent.enabled:
            try:
                node.blend_mode = src.translucent.blend_mode
            except TypeError:
                self._issue(node.name, f"Alpha blend mode '{src.translucent.blend_mode}' is not supported.")
            node.blend_z = src.translucent.zwrite
            node.blend_rshadows = src.translucent.recv_shadows

        if src.cubemap:
            node.reflection_mode = ReflectionMode.CUBEMAP
            node.reflection_cubemap = src.cubemap
        elif src.dynamic_cubemap:
            node.reflection_mode = ReflectionMode.LEVEL
        else:
            node.reflection_mode = ReflectionMode.NONE


    def _import_stage(self, tree: bpy.types.ShaderNodeTree, node_type: type[bpy.types.Node], stage: MaterialStage, index: int) -> bpy.types.Node:
        node = tree.nodes.new(node_type.bl_idname)
        ctx = _Context(tree, stage, f"stage {index}")
        self._apply_fields(node, STAGE_FIELDS[node_type], stage, ctx)
        if node_type is BeamBDSF10Basic and stage.legacy_light.glow_enabled:
            _set_socket(node, BeamBDSF10Basic.Sockets.GLOW_COLOR, from_srgb(list(stage.legacy_light.glow_color)[:3]))
        return node


    def _set_value(self, node: bpy.types.Node, socket_name: str, value: object, ctx: _Context):
        """Sets a socket value, bundle (RGBA) sockets get a linked BNG RGBA node."""
        socket = node.inputs[socket_name]
        if not _is_bundle(socket):
            _set_socket(node, socket_name, value)
            return
        rgba = cast(BeamRGBA, ctx.tree.nodes.new(BeamRGBA.bl_idname))
        rgba.color_value = cast(Tuple4F, value)
        ctx.tree.links.new(rgba.outputs[0], socket)


    def _has_data(self, fields: Sequence[Field], target: object) -> bool:
        for field in fields:
            if isinstance(field, Value):
                obj, name = _resolve(target, field.path)
                if obj.is_set(name): return True
            elif isinstance(field, Tex):
                obj, name = _resolve(target, field.path)
                if any(_get_field(getattr(obj, name), key) is not None for key in _TEX_KEYS): return True
            elif self._has_data(field.fields, target):
                return True
        return False


    def _apply_fields(self, node: bpy.types.Node, fields: Sequence[Field], target: object, ctx: _Context):
        for field in fields:
            if isinstance(field, Value):
                obj, name = _resolve(target, field.path)
                if obj.is_set(name): self._set_value(node, field.socket, INVERSE[field.conv](getattr(obj, name)), ctx)
            elif isinstance(field, Tex):
                self._import_tex(node, field, target, ctx)
            elif self._has_data(field.fields, target):
                helper = ctx.tree.nodes.new(field.node.bl_idname)
                ctx.tree.links.new(helper.outputs[0], node.inputs[field.socket])
                self._apply_fields(helper, field.fields, target, dataclass_replace(ctx, detail=field.detail))


    def _import_tex(self, node: bpy.types.Node, field: Tex, target: object, ctx: _Context):

        obj, name = _resolve(target, field.path)
        socket: TextureSocket = getattr(obj, name)
        tree = ctx.tree

        map: str | None = _get_field(socket, "map")
        if map:
            if _is_bundle(node.inputs[field.map]):
                # RGBA maps need the addon's image node
                image_node = tree.nodes.new(BeamImageTex.bl_idname)
                cast(BeamImageTex, image_node).image = self._get_image(map)
                output = image_node.outputs[BeamImageTex.ImageType.COLOR_RGBA]
            else:
                image_node = tree.nodes.new(NodeName.TexImage)
                cast(bpy.types.ShaderNodeTexImage, image_node).image = self._get_image(map)
                output = image_node.outputs[SocketName.Color]

            if field.normal:
                normal_map = tree.nodes.new(NodeName.NormalMap)
                tree.links.new(output, normal_map.inputs[SocketName.Color])
                strength = _get_field(socket, "value")
                if strength is not None: _set_socket(normal_map, SocketName.Strength, float(strength))
                output = normal_map.outputs[SocketName.Normal]

            tree.links.new(output, node.inputs[field.map])
            self._link_uv(image_node, _get_field(socket, "uv") or 0, dataclass_replace(ctx, detail=ctx.detail or field.detail))

        for key, socket_name, conv in (("value", field.value, INVERSE[field.conv]), ("instance", field.instance, bool), ("vertex", field.vertex, bool)):
            if socket_name is None: continue
            value = _get_field(socket, key)
            if value is not None: self._set_value(node, socket_name, conv(value), ctx)


    def _link_uv(self, image_node: bpy.types.Node, uv: int, ctx: _Context):

        if uv not in (0, 1):
            self._issue(ctx.location, f"UV index {uv} is not supported, using 0.")
            uv = 0

        if uv == 0 and not ctx.detail and not ctx.animated:
            return

        LS = BeamUVData.Sockets
        if ctx.detail:
            output = (LS.DETAIL_UV0, LS.DETAIL_UV1)[uv]
        else:
            output = (LS.UV0, LS.UV1)[uv]
        ctx.tree.links.new(self._get_uv_data(ctx).outputs[output], image_node.inputs[SocketName.Vector])


    def _get_uv_data(self, ctx: _Context) -> bpy.types.Node:

        uv_data = ctx.shared.get("uv_data")
        if uv_data is not None: return uv_data

        uv_data = ctx.tree.nodes.new(BeamUVData.bl_idname)
        ctx.shared["uv_data"] = uv_data
        _set_socket(uv_data, BeamUVData.Sockets.DETAIL_SCALE, tuple(ctx.stage.detail.scale))

        if ctx.animated:
            anim = ctx.tree.nodes.new(BeamUVAnimation.bl_idname)
            ctx.tree.links.new(anim.outputs[BeamUVAnimation.Sockets.ANIMATION], uv_data.inputs[BeamUVData.Sockets.ANIMATION])
            self._import_animation(anim, ctx)

        return uv_data


    def _import_animation(self, node: bpy.types.Node, ctx: _Context):

        self._apply_fields(node, UV_ANIMATION, ctx.stage, ctx)

        LS = BeamUVAnimation.Sockets
        anim = ctx.stage.animation
        flags = AnimationFlags(anim.flags)

        if flags & (AnimationFlags.WAVE | AnimationFlags.SCALE):
            _set_socket(node, LS.WAVE_TYPE, BeamUVAnimation.WaveType(anim.wave_type.value))
            _set_socket(node, LS.WAVE_SCALE, bool(flags & AnimationFlags.SCALE))

        if flags & AnimationFlags.SEQUENCE and anim.seq_segment_size > 0:
            _set_socket(node, LS.FRAMES, round(1 / anim.seq_segment_size))


    def _get_image(self, map: str) -> bpy.types.Image:

        image = bpy.data.images.get(map)
        if image is not None: return image

        image = bpy.data.images.new(map, 1, 1)
        image.source = 'FILE'
        image.filepath = os.path.join(self.base_dir, map) if self.base_dir and not os.path.isabs(map) else map
        not_none(image.colorspace_settings).name = ColorSpace.NON_COLOR.value # pyright: ignore[reportAttributeAccessIssue]
        return image
