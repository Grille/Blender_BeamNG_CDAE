from __future__ import annotations

from grille_cdae.common import *
from grille_cdae.enums import *

from ...blender.material_properties import MaterialProperties
from ...blender.node_walker import NodeWalker
from ...blender.shader_nodes import BeamMaterial, BeamBSDFCollision, BeamImageTex, BeamUVData, ReflectionMode
from .material import *
from .node_fields import Field, Tex, Value, STAGE_FIELDS, STAGE_UNSUPPORTED, MATERIAL_FIELDS, to_float



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



_UV_DATA_INDEX = {
    BeamUVData.Sockets.UV0: 0,
    BeamUVData.Sockets.UV1: 1,
}

# value sources that can be read without evaluating the node tree
_CONSTANT_NODES = (NodeName.Value, NodeName.RGB)


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


    def build_from_bmat(self, bmat: bpy.types.Material) -> Material:

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
        else:
            raise MaterialExportError(f"Expected '{BeamMaterial.bl_label}' on Material Output > Surface, found '{not_none(walker.current).bl_label}'.")

        return mat


    def _issue(self, location: str, message: str):
        self.issues.append(ExportIssue(str(self.material.name), location, message))


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
        location = node.name

        self._apply_fields(walker, MATERIAL_FIELDS, mat, location)

        if mat.alpha_test:
            mat.alpha_ref = round(self._read_value(walker, BeamMaterial.Sockets.CLIP_T, location) * 255)
        if not mat.double_sided:
            mat.invert_backface_normals = False

        subsurface = to_float(self._read_value(walker, BeamMaterial.Sockets.SUBSURFACE_SCATTERING, location))
        mat.subsurface.enabled = subsurface > 0
        if subsurface > 0: mat.subsurface.intensity = subsurface

        if node.blend_mode != AlphaBlendMode.NONE:
            mat.translucent.enabled = True
            mat.translucent.blend_mode = AlphaBlendMode(node.blend_mode)
            mat.translucent.zwrite = node.blend_z
            mat.translucent.recv_shadows = node.blend_rshadows

        mat.dynamic_cubemap = node.reflection_mode == ReflectionMode.LEVEL
        if node.reflection_mode == ReflectionMode.CUBEMAP:
            mat.cubemap = node.reflection_cubemap

        stage_walker = walker.fork()
        if not stage_walker.try_follow(SocketName.BNGShader):
            raise MaterialExportError(f"Nothing linked to '{BeamMaterial.bl_label}' > {SocketName.BNGShader}.")

        self._build_stages(stage_walker)


    def _build_stages(self, walker: NodeWalker):

        node = not_none(walker.current)
        fields = STAGE_FIELDS.get(type(node))
        if fields is None:
            raise MaterialExportError(f"'{node.bl_label}' is not supported as stage yet.")

        mat = self.material
        mat.version = MaterialVersion.V1_5
        mat.active_layers = 1

        location = f"{node.name} (stage 0)"
        for socket in STAGE_UNSUPPORTED.get(type(node), ()):
            if walker.is_linked(socket):
                self._issue(location, f"'{socket}' is not exported yet.")

        self._apply_fields(walker, fields, mat.stages[0], location)


    def _apply_fields(self, walker: NodeWalker, fields: Sequence[Field], target: object, location: str):
        for field in fields:
            if isinstance(field, Value):
                obj, name = _resolve(target, field.path)
                setattr(obj, name, field.conv(self._read_value(walker, field.socket, location)))
            else:
                self._apply_tex(walker, field, target, location)


    def _apply_tex(self, walker: NodeWalker, field: Tex, target: object, location: str):

        obj, name = _resolve(target, field.path)
        socket: TextureSocket = getattr(obj, name)

        def set_field(key: str, value: object):
            try:
                socket.set_field(key, value)
            except KeyError:
                self._issue(location, f"'{field.map}': BeamNG has no '{key}' for this map.")

        ref = self._find_image(walker, field.map, location)
        if ref is not None:
            socket.set_field("map", ref.image.name)
            if ref.uv != 0: set_field("uv", ref.uv)
            if field.normal and ref.strength is not None: set_field("value", to_float(ref.strength))

        if field.value is not None:
            set_field("value", field.conv(self._read_value(walker, field.value, location)))
        if field.instance is not None:
            set_field("instance", bool(self._read_value(walker, field.instance, location)))
        if field.vertex is not None:
            set_field("vertex", bool(self._read_value(walker, field.vertex, location)))


    def _read_value(self, walker: NodeWalker, socket_name: str, location: str) -> Any:

        input = not_none(walker.get_input(socket_name))
        if not input.is_linked:
            return butils.get_default_value(input)

        source = walker.fork()
        if not source.try_follow(socket_name):
            # unlinked node group input, use the value of the group node socket
            if source.last_socket_value is not None: return source.last_socket_value
            return butils.get_default_value(input)

        node = not_none(source.current)
        if source.is_node_any_idname(*_CONSTANT_NODES):
            return butils.get_default_value(node.outputs[0])

        self._issue(location, f"'{socket_name}' is linked to '{node.bl_label}', only plain values can be exported, using the socket value.")
        return butils.get_default_value(input)


    def _find_image(self, walker: NodeWalker, socket_name: str, location: str) -> _ImageRef | None:

        source = walker.fork()
        if not source.try_follow(socket_name):
            return None

        strength: float | None = None

        if source.is_node_idname(NodeName.NormalMap):
            strength = source.get_float_value(SocketName.Strength)
            if not source.try_follow(SocketName.Color):
                return None

        node = not_none(source.current)
        if source.is_node_idname(NodeName.TexImage):
            image = cast(bpy.types.ShaderNodeTexImage, node).image
        elif source.is_node_idname(BeamImageTex):
            image = cast(BeamImageTex, node).image
            if source.last_socket_name == BeamImageTex.ImageType.NORMAL:
                strength = source.get_float_value(SocketName.Strength)
        else:
            self._issue(location, f"'{socket_name}' expects an image texture, found '{node.bl_label}'.")
            return None

        if image is None:
            self._issue(location, f"'{socket_name}': image texture node '{node.name}' has no image.")
            return None

        return _ImageRef(image, self._find_uv(source, location), strength)


    def _find_uv(self, image_walker: NodeWalker, location: str) -> int:

        source = image_walker.fork()
        if not source.try_follow(SocketName.Vector):
            return 0

        node = not_none(source.current)
        if source.is_node_idname(BeamUVData):
            uv = _UV_DATA_INDEX.get(BeamUVData.Sockets(source.last_socket_name), None)
            if uv is None:
                self._issue(location, f"'{node.name}' > {source.last_socket_name} is not exported yet, using UV 0.")
                return 0
            if source.is_linked(BeamUVData.Sockets.ANIMATION):
                self._issue(location, f"'{node.name}': UV animation is not exported yet.")
            return uv

        if source.is_node_idname(NodeName.UVMap):
            uv_map: str = cast(bpy.types.ShaderNodeUVMap, node).uv_map
            return 1 if self.uv1_hint and self.uv1_hint.lower() in uv_map.lower() else 0

        self._issue(location, f"'{node.bl_label}' as image UV source is not supported, using UV 0.")
        return 0
