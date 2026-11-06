from __future__ import annotations

from dataclasses import field as dataclass_field, replace as dataclass_replace

from grille_cdae.common import *
from grille_cdae.enums import *

from ...blender.material_properties import MaterialProperties
from ...blender.node_walker import NodeWalker
from ...blender.shader_nodes import (
    BaseBeamRGBA, BeamMaterial, BeamBSDFCollision, BeamBDSF10Basic, BeamImageTex, BeamImageTexConverter, BeamStageMix, BeamUVData, BeamUVAnimation, ImageType, ReflectionMode
)
from .material import *
from .node_fields import Field, Tex, Value, Bundle, STAGE_FIELDS, STAGE_VERSION, CONVERT_FIELDS, MATERIAL_FIELDS, UV_ANIMATION, UV_ANIMATION_FLAGS, UV_ANIMATION_MOTION, to_float, to_srgb, to_vec2



class MaterialExportError(Exception):
    """The material can't be exported at all."""



@dataclass
class ExportIssue:
    material: str
    location: str
    message: str

    def __str__(self): return f"{self.material} [{self.location}]: {self.message}"



@dataclass
class _ImageRef:
    image: bpy.types.Image
    uv: int
    strength: float | None



@dataclass
class _Context:
    """State while applying the fields of one node (tree), shared per stage."""
    location: str
    detail: bool = False
    # stage wide settings, reachable from several maps, written once per stage
    detail_scales: list[Vec2F] = dataclass_field(default_factory=list[Vec2F])
    animations: list[bpy.types.Node] = dataclass_field(default_factory=list[bpy.types.Node])



MAX_STAGES = 4

_UV_DATA_INDEX = {
    BeamUVData.Sockets.UV0: (0, False),
    BeamUVData.Sockets.UV1: (1, False),
    BeamUVData.Sockets.DETAIL_UV0: (0, True),
    BeamUVData.Sockets.DETAIL_UV1: (1, True),
}

# value sources that can be read without evaluating the node tree
_CONSTANT_NODES = (NodeName.Value, NodeName.RGB)

_SEPARATE_COLOR_NODES = ("ShaderNodeSeparateColor", "ShaderNodeSeparateRGB")


def _resolve(root: object, path: str) -> tuple[Any, str]:
    *parents, name = path.split(".")
    for parent in parents: root = getattr(root, parent)
    return root, name



class MaterialBuilder:
    """Builds a clean BeamNG material from a node tree made of the addon's shader nodes."""

    def __init__(self, default_version = MaterialVersion.V1_5):
        self.material = Material({})
        self.default_version = default_version
        self.uv1_hint = "1"
        self.issues: list[ExportIssue] = []


    def build_from_bmat(self, bmat: bpy.types.Material, convert: bool = False) -> Material:
        """`convert` also reads Blender's Principled / Diffuse BSDF (to convert them to BeamNG nodes), the version is left unset then."""

        mat = self.material
        mat.name = bmat.name
        mat.map_to = bmat.name
        mat.class_name = "Material"
        mat.ground_type = MaterialProperties.get_ground_type(bmat) or None

        if bmat.node_tree is None:
            mat.version = self.default_version
            return mat

        walker = NodeWalker()
        if not walker.find_material_output(bmat.node_tree.nodes):
            raise MaterialExportError("No active Material Output node.")
        if not walker.try_follow(SocketName.Surface):
            raise MaterialExportError("Nothing linked to Material Output > Surface.")

        if walker.is_node_idname(BeamBSDFCollision):
            self._build_collision()
        elif walker.is_node_idname(BeamMaterial):
            self._build_material(walker)
        elif convert and type(walker.current) in CONVERT_FIELDS:
            self._build_converted(walker)
        else:
            raise MaterialExportError(f"Expected '{BeamMaterial.bl_label}' on Material Output > Surface, found '{not_none(walker.current).bl_label}'.")

        return mat


    def _issue(self, location: str, message: str):
        self.issues.append(ExportIssue(str(self.material.name), location, message))


    def _build_converted(self, walker: NodeWalker):

        node = not_none(walker.current)
        stage = self.material.stages[0]
        ctx = _Context(node.name)

        self._apply_fields(walker, CONVERT_FIELDS[type(node)], stage, ctx)

        if walker.has_input("Emission Strength") and to_float(self._read_value(walker, "Emission Strength", ctx)) == 0:
            stage.emission.map = None
            stage.emission.factor = None

        if not stage.clear_coat.map and stage.clear_coat.factor == 0:
            stage.clear_coat.roughness = None

        # alpha of the base color image, BeamNG uses the base color alpha without an opacity map
        if stage.opacity.map and stage.opacity.map == stage.color.map:
            stage.opacity.map = None
            stage.opacity.uv = None


    def _build_collision(self):
        mat = self.material
        mat.version = MaterialVersion.V1
        mat.stages[0].color.factor = Color4F(1, 0, 1, 0)
        mat.alpha_test = True
        mat.alpha_ref = 255
        mat.cast_shadows = False


    def _build_material(self, walker: NodeWalker):

        mat = self.material
        node = cast(BeamMaterial, walker.current)
        ctx = _Context(node.name)

        self._apply_fields(walker, MATERIAL_FIELDS, mat, ctx)

        if mat.alpha_test:
            mat.alpha_ref = round(self._read_value(walker, BeamMaterial.Sockets.CLIP_T, ctx) * 255)
        if not mat.double_sided:
            mat.invert_backface_normals = False

        subsurface = to_float(self._read_value(walker, BeamMaterial.Sockets.SUBSURFACE_SCATTERING, ctx))
        mat.subsurface.enabled = subsurface > 0
        if subsurface > 0: mat.subsurface.intensity = subsurface

        mat.translucent.blend_mode = AlphaBlendMode(node.blend_mode)
        if mat.translucent.blend_mode != AlphaBlendMode.NONE:
            mat.translucent.zwrite = node.blend_z
            mat.translucent.recv_shadows = node.blend_rshadows

        mat.dynamic_cubemap = node.reflection_mode == ReflectionMode.LEVEL
        if node.reflection_mode == ReflectionMode.CUBEMAP:
            mat.cubemap = node.reflection_cubemap

        stage_walker = walker.fork()
        if not stage_walker.try_follow(SocketName.BNGShader):
            raise MaterialExportError(f"Nothing linked to '{BeamMaterial.bl_label}' > {SocketName.BNGShader}.")

        self._build_stages(stage_walker)


    def _collect_stages(self, walker: NodeWalker, stages: list[NodeWalker]):
        """Flattens stage mix nodes, base before overlay."""

        if not walker.is_node_idname(BeamStageMix):
            stages.append(walker)
            return

        for socket in BeamStageMix.Sockets:
            source = walker.fork()
            if source.try_follow(socket):
                self._collect_stages(source, stages)
            else:
                self._issue(not_none(walker.current).name, f"Nothing linked to '{socket}'.")


    def _build_stages(self, walker: NodeWalker):

        stages: list[NodeWalker] = []
        self._collect_stages(walker, stages)

        if len(stages) == 0:
            raise MaterialExportError("No stage found.")
        if len(stages) > MAX_STAGES:
            raise MaterialExportError(f"{len(stages)} stages, BeamNG supports at most {MAX_STAGES}.")

        nodes = [not_none(stage_walker.current) for stage_walker in stages]
        for node in nodes:
            if type(node) not in STAGE_FIELDS:
                raise MaterialExportError(f"'{node.bl_label}' is not supported as stage.")
        if len(set(type(node) for node in nodes)) > 1:
            raise MaterialExportError(f"Stages of different material versions can't be mixed: {', '.join(node.bl_label for node in nodes)}.")

        mat = self.material
        mat.version = STAGE_VERSION[type(nodes[0])]
        mat.active_layers = len(stages)

        for index, (stage_walker, node) in enumerate(zip(stages, nodes)):
            stage = mat.stages[index]
            ctx = _Context(f"{node.name} (stage {index})")
            self._apply_fields(stage_walker, STAGE_FIELDS[type(node)], stage, ctx)
            if isinstance(node, BeamBDSF10Basic):
                self._apply_glow(stage_walker, stage, ctx)
            self._apply_detail_scale(stage, ctx)
            self._apply_animation(stage, ctx)


    def _apply_glow(self, walker: NodeWalker, stage: MaterialStage, ctx: _Context):
        color = to_srgb(self._read_value(walker, BeamBDSF10Basic.Sockets.GLOW_COLOR, ctx))
        if any(c > 0 for c in color[:3]):
            stage.legacy_light.glow_enabled = True
            stage.legacy_light.glow_color = color


    def _apply_fields(self, walker: NodeWalker, fields: Sequence[Field], target: object, ctx: _Context):
        for field in fields:
            if isinstance(field, Value):
                value = self._read_value(walker, field.socket, ctx)
                if value is None: continue
                obj, name = _resolve(target, field.path)
                setattr(obj, name, field.conv(value))
            elif isinstance(field, Tex):
                self._apply_tex(walker, field, target, ctx)
            else:
                self._apply_bundle(walker, field, target, ctx)


    def _apply_bundle(self, walker: NodeWalker, field: Bundle, target: object, ctx: _Context):

        source = walker.fork()
        if not source.try_follow(field.socket):
            return

        if not source.is_node_idname(field.node):
            self._issue(ctx.location, f"'{field.socket}' expects '{field.node.bl_label}', found '{not_none(source.current).bl_label}'.")
            return

        self._apply_fields(source, field.fields, target, dataclass_replace(ctx, detail=field.detail))


    def _apply_tex(self, walker: NodeWalker, field: Tex, target: object, ctx: _Context):

        obj, name = _resolve(target, field.path)
        socket: TextureSocket = getattr(obj, name)

        def set_field(key: str, value: object):
            try:
                socket.set_field(key, value)
            except KeyError:
                self._issue(ctx.location, f"'{field.map}': BeamNG has no '{key}' for this map.")

        ref = self._find_image(walker, field.map, dataclass_replace(ctx, detail=ctx.detail or field.detail))
        if ref is not None:
            socket.set_field("map", ref.image.name)
            if ref.uv != 0: set_field("uv", ref.uv)
            if field.normal and ref.strength is not None: set_field("value", to_float(ref.strength))

        def read(socket_name: str | None, conv: Converter[object]):
            if socket_name is None: return None
            # map and value on the same socket (Blender nodes): a linked socket's value isn't used
            if socket_name == field.map and walker.is_linked(socket_name): return None
            value = self._read_value(walker, socket_name, ctx)
            return None if value is None else conv(value)

        for key, value in (("value", read(field.value, field.conv)), ("instance", read(field.instance, bool)), ("vertex", read(field.vertex, bool))):
            if value is not None: set_field(key, value)


    def _apply_detail_scale(self, stage: MaterialStage, ctx: _Context):
        scales = list(dict.fromkeys(ctx.detail_scales))
        if len(scales) == 0: return
        if len(scales) > 1:
            self._issue(ctx.location, f"Detail maps use different detail scales {[tuple(s) for s in scales]}, BeamNG has one per stage, using the first.")
        stage.detail.scale = scales[0]


    def _apply_animation(self, stage: MaterialStage, ctx: _Context):

        nodes = list(dict.fromkeys(ctx.animations))
        if len(nodes) == 0: return
        if len(nodes) > 1:
            self._issue(ctx.location, f"Maps use different UV animations {[n.name for n in nodes]}, BeamNG has one per stage, using '{nodes[0].name}'.")

        walker = NodeWalker(nodes[0])
        anim_ctx = _Context(nodes[0].name)

        LS = BeamUVAnimation.Sockets
        AF = AnimationFlags
        anim = stage.animation

        motion: str = self._read_value(walker, LS.MOTION, anim_ctx)
        flags = UV_ANIMATION_MOTION.get(motion)
        if flags is None:
            self._issue(anim_ctx.location, f"Unknown motion '{motion}'.")
            flags = AF.NONE
        for flag, socket in UV_ANIMATION_FLAGS.items():
            if self._read_value(walker, socket, anim_ctx): flags |= flag
        wave_value: str = self._read_value(walker, LS.WAVE_TYPE, anim_ctx)
        if wave_value != BeamUVAnimation.WaveType.NONE:
            if wave_value in AnimationWaveType: flags |= AF.WAVE
            else: self._issue(anim_ctx.location, f"Unknown wave type '{wave_value}'.")

        # drop what has no effect: wave without motion or scale, scale without wave or sequence
        if not flags & (AF.SCROLL | AF.ROTATION | AF.SCALE): flags &= ~AF.WAVE
        if not flags & (AF.WAVE | AF.SEQUENCE): flags &= ~AF.SCALE
        if AF.SCROLL in flags and (AF.WAVE | AF.SCALE) in flags:
            self._issue(anim_ctx.location, f"'{BeamUVAnimation.Motion.SCROLL.value}' has no effect with a '{LS.WAVE_TYPE.value}' and '{LS.SCALE.value}', the wave scale resets the offset.")
            flags &= ~AF.SCROLL

        for field, used in UV_ANIMATION:
            if used(flags): self._apply_fields(walker, (field,), stage, anim_ctx)

        if flags & AnimationFlags.WAVE:
            anim.wave_type = AnimationWaveType(wave_value)

        if flags & AnimationFlags.SEQUENCE:
            frames = to_float(self._read_value(walker, LS.FRAMES, anim_ctx))
            if frames > 0: anim.seq_segment_size = to_float(1 / frames)
            else: self._issue(anim_ctx.location, f"'{LS.SEQUENCE.value}' needs more than 0 '{LS.FRAMES.value}'.")

        anim.flags = flags


    def _read_value(self, walker: NodeWalker, socket_name: str, ctx: _Context) -> Any:
        """Value of a plain socket, or of the constant node linked to it. None for an unlinked socket without value (bundle)."""

        input = not_none(walker.get_input(socket_name))
        has_value = hasattr(input, "default_value")
        def own_value(): return butils.get_default_value(input) if has_value else None

        if not input.is_linked:
            return own_value()

        source = walker.fork()
        if not source.try_follow(socket_name):
            # unlinked node group input, use the value of the group node socket
            if source.last_socket_value is not None: return source.last_socket_value
            return own_value()

        node = not_none(source.current)
        if source.is_node_any_idname(*_CONSTANT_NODES):
            return butils.get_default_value(node.outputs[0])
        if isinstance(node, BaseBeamRGBA):
            return tuple(node.color_value)

        self._issue(ctx.location, f"'{socket_name}' is linked to '{node.bl_label}', only plain values can be exported" + (", using the socket value." if has_value else "."))
        return own_value()


    def _find_image(self, walker: NodeWalker, socket_name: str, ctx: _Context) -> _ImageRef | None:

        source = walker.fork()
        if not source.try_follow(socket_name):
            return None

        strength: float | None = None

        if source.is_node_idname(NodeName.NormalMap):
            strength = source.get_float_value(SocketName.Strength)
            if not source.try_follow(SocketName.Color):
                return None

        alpha: NodeWalker | None = None
        if source.is_node_idname(BeamImageTexConverter):
            CS = BeamImageTexConverter.Sockets
            if source.last_socket_name == ImageType.NORMAL:
                strength = source.get_float_value(CS.STRENGTH)
            if source.last_socket_name == ImageType.COLOR_RGBA:
                alpha = source.fork()
                if not alpha.try_follow(CS.ALPHA): alpha = None
            if not source.try_follow(CS.COLOR):
                return None

        channel: str | None = None
        if source.is_node_any_idname(*_SEPARATE_COLOR_NODES):
            channel = source.last_socket_name
            if not source.try_follow(0):
                return None

        node = not_none(source.current)
        if source.is_node_idname(NodeName.TexImage):
            image = cast(bpy.types.ShaderNodeTexImage, node).image
        elif source.is_node_idname(BeamImageTex):
            image = cast(BeamImageTex, node).image
            if source.last_socket_name == BeamImageTex.Sockets.NORMAL:
                strength = source.get_float_value(SocketName.Strength)
        else:
            self._issue(ctx.location, f"'{socket_name}' expects an image texture, found '{node.bl_label}'.")
            return None

        if image is None:
            self._issue(ctx.location, f"'{socket_name}': image texture node '{node.name}' has no image.")
            return None

        if channel is not None:
            self._issue(ctx.location, f"'{socket_name}' uses the {channel} channel of '{image.name}', BeamNG reads data maps from the red channel, the image needs that channel split into its own map.")

        if alpha is not None and alpha.current is not node:
            alpha_image = alpha.get_image() if alpha.is_node_any_idname(NodeName.TexImage, BeamImageTex) else None
            alpha_source = not_none(alpha.current).name if alpha_image is None else alpha_image.name
            self._issue(ctx.location, f"'{socket_name}': the alpha of '{image.name}' comes from '{alpha_source}', BeamNG uses the alpha channel of the same image.")

        return _ImageRef(image, self._find_uv(source, ctx), strength)


    def _find_uv(self, image_walker: NodeWalker, ctx: _Context) -> int:

        source = image_walker.fork()
        if not source.try_follow(SocketName.Vector):
            if ctx.detail: ctx.detail_scales.append(Vec2F.ONE)
            return 0

        node = not_none(source.current)
        if source.is_node_idname(BeamUVData):
            uv, is_detail_uv = _UV_DATA_INDEX[BeamUVData.Sockets(source.last_socket_name)]

            if is_detail_uv and not ctx.detail:
                self._issue(ctx.location, f"'{node.name}' > {source.last_socket_name} is used for a non detail map, the detail scale is ignored.")
            elif ctx.detail:
                scale = to_vec2(self._read_value(source, BeamUVData.Sockets.DETAIL_SCALE, ctx)) if is_detail_uv else Vec2F.ONE
                ctx.detail_scales.append(scale)

            animation = source.fork()
            if animation.try_follow(BeamUVData.Sockets.ANIMATION):
                if animation.is_node_idname(BeamUVAnimation):
                    ctx.animations.append(not_none(animation.current))
                else:
                    self._issue(ctx.location, f"'{node.name}' > {BeamUVData.Sockets.ANIMATION} expects '{BeamUVAnimation.bl_label}'.")
            return uv

        if ctx.detail: ctx.detail_scales.append(Vec2F.ONE)

        if source.is_node_idname(NodeName.UVMap):
            uv_map: str = cast(bpy.types.ShaderNodeUVMap, node).uv_map
            return 1 if self.uv1_hint and self.uv1_hint.lower() in uv_map.lower() else 0

        self._issue(ctx.location, f"'{node.bl_label}' as image UV source is not supported, using UV 0.")
        return 0
