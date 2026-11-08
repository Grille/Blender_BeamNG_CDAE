from __future__ import annotations

from bpy.types import Context, UILayout
from grille_cdae.common import *
from grille_cdae.common.basetypes import ShaderNodeCustomGroup, Menu

from grille_cdae.enums import *

from .material_properties import *
from .shader_nodes_utils import *
from .shader_node_builder import NodeGroupBuilder, SocketCreateInfo, NodeGroupData, NodeSignature, LinkSource, LinkBuilderBase
_SCI = SocketCreateInfo



NODE_GROUP_JSON_KEY = "grille_beamng_cdae_ngjson"
NODE_GROUP_VERSION_MAYOR_KEY = "grille_beamng_cdae_mayor_version"
NODE_GROUP_VERSION_MINOR_KEY = "grille_beamng_cdae_minor_version"
SHADER_NODE_PREFIX = "ShaderNodeCustom.grille_beamng_cdae_"

RGBA = NodeSignature(
    (SocketName.Color, SocketType.Color),
    (SocketName.Alpha, SocketType.Float),
    (SocketName.Enabled, SocketType.Bool),
)

PAINT_LAYER = NodeSignature(
    (SocketName.Color, SocketType.Color),
    (SocketName.Alpha, SocketType.Float),
    (SocketName.Metallic, SocketType.Float),
    (SocketName.Roughness, SocketType.Float),
    (SocketName.ClearCoat, SocketType.Float),
    (SocketName.ClearCoatRoughness, SocketType.Float),
    (SocketName.Enabled, SocketType.Bool),
)
DETAIL_LAYER = NodeSignature(
    (SocketName.Color, SocketType.Color),
    (SocketName.Alpha, SocketType.Float),
    (SocketName.Normal, SocketType.Vector),
    (SocketName.Metallic, SocketType.Float),
    (SocketName.Roughness, SocketType.Float),
    (SocketName.AmbientOcclusion, SocketType.Float),
    (SocketName.Enabled, SocketType.Bool),
)

PAINT3 = NodeSignature(
    ("Layer 1", PAINT_LAYER),
    ("Layer 2", PAINT_LAYER),
    ("Layer 3", PAINT_LAYER),
)
PALETTE = NodeSignature(
    (SocketName.Vector, SocketType.Vector),
    (SocketName.Color, SocketType.Bool),
    (SocketName.Metallic, SocketType.Bool),
    (SocketName.Roughness, SocketType.Bool),
    (SocketName.ClearCoat, SocketType.Bool),
    (SocketName.ClearCoatRoughness, SocketType.Bool),
)
DISPLAY_INFO = NodeSignature(
    (SocketName.Paint, PAINT3),
    (SocketName.VertexColor, RGBA),
    (SocketName.AmbientOcclusionStrength, SocketType.Float),
    (SocketName.Enabled, SocketType.Bool),
)

BNGS_INPUT = NodeSignature(
    (SocketName.ReflectionMode, SocketType.Integer),
    (SocketName.AlphaBlendMode, SocketType.Integer),
    (SocketName.InvertBackfaceNormals, SocketType.Bool),
    (SocketName.SubsurfaceScattering, SocketType.Float),
    (SocketName.DisplayInfo, DISPLAY_INFO)
)
BNGS_OUTPUT = NodeSignature(
    (SocketName.Shader, SocketType.Shader),
    (SocketName.Alpha, SocketType.Float)
)
UVMATRIX = NodeSignature(
    ("U", SocketType.Vector),
    ("V", SocketType.Vector),
    (SocketName.Enabled, SocketType.Bool),
)
BNGS_IO = NodeSignature.IO(BNGS_INPUT, BNGS_OUTPUT)

# socket shapes tell the user what an input expects
NODE_SOCKET_SHAPE = SocketShape.CIRCLE  # another node, neither a texture nor a constant
TEXTURE_SOCKET_SHAPE = SocketShape.DIAMOND  # a texture
VALUE_SOCKET_SHAPE = SocketShape.LINE  # a constant
TVMIX_SOCKET_SHAPE = SocketShape.SQUARE  # a texture, a constant or a node tree, only used for normals
DISPLAY_SOCKET_SHAPE = SocketShape.CIRCLE_DOT  # only affects the viewport, not exported

COLOR_WHITE = Color4F.WHITE
COLOR_BLACK = Color4F.BLACK
COLOR_GRAY = (0.5,0.5,0.5,1)
COLOR_NULL = (0,0,0,0)
COLOR_NULL_HALF = (0.5,0.5,0.5,0.5)
COLOR_RED = (1,0,0,1)
COLOR_MAGENTA = (1,0,1,1)

_BOOL = _SCI.BOOL
_BOOL_VALUE = _SCI(SocketType.Bool, VALUE_SOCKET_SHAPE, False)
_BOOL_DISPLAY = _SCI(SocketType.Bool, DISPLAY_SOCKET_SHAPE, False)
_MENU = _SCI(SocketType.Menu, VALUE_SOCKET_SHAPE, False)
_FLOAT = _SCI.FACTOR
_FLOAT_VALUE = _SCI(SocketType.Float, VALUE_SOCKET_SHAPE, False, default_value=1, **_SCI.FACTOR.kwargs)
_FLOAT_ANY_VALUE = _SCI(SocketType.Float, VALUE_SOCKET_SHAPE, False, default_value=0)
_FLOAT_TEXTURE = _SCI(SocketType.Float, TEXTURE_SOCKET_SHAPE, True, default_value=1)
_FLOAT_DISPLAY = _SCI(SocketType.Float, DISPLAY_SOCKET_SHAPE, False, default_value=1)
_COLOR = _SCI.COLOR
_COLOR_VALUE = _SCI(SocketType.Color, VALUE_SOCKET_SHAPE, False, default_value=COLOR_WHITE)
_COLOR_TEXTURE = _SCI(SocketType.Color, TEXTURE_SOCKET_SHAPE, True, default_value=COLOR_WHITE)
_COLOR_DISPLAY = _SCI(SocketType.Color, DISPLAY_SOCKET_SHAPE, False, default_value=COLOR_WHITE)
_RGBA_X = _SCI(SocketType.Bundle)
_RGBA_VALUE = _SCI(SocketType.Bundle, VALUE_SOCKET_SHAPE, False)
_RGBA_TEXTURE = _SCI(SocketType.Bundle, TEXTURE_SOCKET_SHAPE, True)
_NORMAL_TEXTURE = _SCI(SocketType.Vector, TEXTURE_SOCKET_SHAPE, True)
_NORMAL_MIX = _SCI(SocketType.Vector, TVMIX_SOCKET_SHAPE, True)
_BUNDLE_NODE = _SCI(SocketType.Bundle, NODE_SOCKET_SHAPE)
_UV_NODE = _SCI(SocketType.Vector, NODE_SOCKET_SHAPE, True)
_INT_PRIVATE = _SCI(SocketType.Integer, DISPLAY_SOCKET_SHAPE, False, hide_socket=True)
_BUNDLE_DISPLAY = _SCI(SocketType.Bundle, DISPLAY_SOCKET_SHAPE)
_VEC2_VALUE = _SCI(SocketType.Vector, VALUE_SOCKET_SHAPE, **_SCI.VEC2.kwargs)
_VEC3 = _SCI.VEC3



class _Extended_NGB(NodeGroupBuilder):

    def RGBA_seperate(self, value: LinkBuilderBase):
        return self.nc.seperate_bundle(RGBA, value)

    def RGBA_default(self, value: LinkBuilderBase, default_value: LinkSource = COLOR_WHITE):
        return self.nc.node(BeamRGBADefault, value, color_value=default_value)

    def RGBA_input(self, name: str, default_value: Tuple4F | None = None, sci = _RGBA_VALUE):
        value = self.input(sci, name)
        if default_value is None:
            return self.RGBA_seperate(value)
        else:
            return self.RGBA_seperate(self.RGBA_default(value, default_value))

    def RGBA_combine(self, color: LinkSource, alpha: LinkSource):
        return self.nc.combine_bundle(RGBA, color, alpha, True)

    def RGBA_output(self, name: str, color: LinkSource, alpha: LinkSource):
        self.RGBA_combine(color, alpha) >> self.output(SocketType.Bundle, name)



class NodeRuntimeData:

    _node_runtime_dict: dict[int, "NodeRuntimeData"] = {}


    @staticmethod
    def get_instance(node: 'BaseShaderNode'):
        dict = NodeRuntimeData._node_runtime_dict
        key = node.as_pointer()
        data = dict.get(key)
        if data is None:
            data = NodeRuntimeData()
            dict[key] = data
        return data


    def __init__(self):
        self.messages: list[str] = []
        self.updating = False



_NODE_GROUP_DATA_RUNTIME_DICT: dict[str, NodeGroupData] = {}  # keyed by the stored json, pointers get reused after reload / undo



class SavedSocket:
    """A socket's state, carried over by name through a major group update."""

    __slots__ = "type", "value", "changed", "hide", "links"
    def __init__(self, type: str, value: SocketValue | None, changed: bool, hide: bool, links: list[bpy.types.NodeSocket]):
        self.type = type
        self.value = value
        self.changed = changed
        self.hide = hide
        self.links = links


    @staticmethod
    def copy_value(socket: bpy.types.NodeSocket | bpy.types.NodeTreeInterfaceSocket) -> SocketValue | None:
        """Arrays are copied, the socket goes away with the group."""
        if not hasattr(socket, "default_value"): return None
        value = butils.get_default_value(socket)
        return value if isinstance(value, (str, bool, int, float)) else cast(SocketValue, tuple(value))


    @staticmethod
    def save(socket: bpy.types.NodeSocket, links: list[bpy.types.NodeSocket], default: SocketValue | None = None):
        value = SavedSocket.copy_value(socket)
        return SavedSocket(socket.type, value, value is not None and value != default, socket.hide, links)


    def restore(self, socket: bpy.types.NodeSocket, link: Callable[[bpy.types.NodeSocket], object]):
        """Returns False when a changed value couldn't be carried over, unchanged values keep the new default."""
        for other in self.links: link(other)
        if self.hide: socket.hide = True
        if not self.changed: return True
        if socket.type != self.type: return False
        try: butils.set_default_value(socket, cast(SocketValue, self.value))
        except (TypeError, ValueError): return False
        return True


def _BaseShaderNode_init(self: BaseShaderNode, ctx: bpy.types.Context):
    return self.init(ctx)


def _BaseShaderNode_post_init(self: BaseShaderNode, ctx: bpy.types.Context):
    return self.post_init()


class BaseShaderNode(ShaderNodeCustomGroup):

    bl_idname = f"{SHADER_NODE_PREFIX}BaseNode"
    bl_label = "BNG Node"
    bl_icon = 'NONE'
    tree_type = NodeName.ShaderNodeTree
    ng_color_tag: GroupColorTag = GroupColorTag.NONE
    ng_version_mayor: int = 0
    ng_version_minor: int = 0
    ng_shared: bool = True


    @property
    def runtime(self) -> NodeRuntimeData:
        return NodeRuntimeData.get_instance(self)


    @property
    def node_tree_version(self):
        def get(key: str) -> int: return -2 if self.node_tree is None else self.node_tree.get(key, -1)
        mayor = get(NODE_GROUP_VERSION_MAYOR_KEY)
        minor = get(NODE_GROUP_VERSION_MINOR_KEY)
        return (mayor, minor)


    @property
    def is_node_group_outdated(self):
        version = self.node_tree_version
        return self.ng_version_mayor > version[0] or self.ng_version_minor > version[1]


    @property
    def is_node_group_minor_outdated(self):
        """Same interface, the group can be swapped without touching links or values."""
        version = self.node_tree_version
        return self.ng_version_mayor == version[0] and self.ng_version_minor > version[1]


    @property
    def is_node_group_mayor_outdated(self):
        """Interface changed, the node tree may need fixing after the update."""
        return self.node_tree is not None and self.ng_version_mayor > self.node_tree_version[0]


    @classmethod
    def poll(cls, node_tree):
        if node_tree is None: return False
        return node_tree.bl_idname == NodeName.ShaderNodeTree
    

    def get_validator(self):
        return NodeLayoutValidator(self, None, self.runtime.messages)


    def init(self, context):
        self.node_tree = self.get_node_group()
        self.apply_socket_data()
        self.post_init()


    def apply_socket_data(self):
        """Socket shapes live on the node, not the group interface, so they are applied per node."""
        tree = self.node_tree
        if tree is None or NODE_GROUP_JSON_KEY not in tree: return

        text = tree[NODE_GROUP_JSON_KEY]
        ngdata = _NODE_GROUP_DATA_RUNTIME_DICT.get(text, None)
        if ngdata is None:
            ngdata =  NodeGroupData.from_text(text)
            _NODE_GROUP_DATA_RUNTIME_DICT[text] = ngdata

        for key in ngdata.inputs: ngdata.inputs[key].apply(self.inputs[key])
        for key in ngdata.outputs: ngdata.outputs[key].apply(self.outputs[key])


    def post_init(self):
        pass


    def get_interface_defaults(self) -> dict[str, SocketValue]:
        """Input identifier -> the group's default value."""
        if self.node_tree is None: return {}
        return {
            item.identifier: not_none(SavedSocket.copy_value(item)) for item in not_none(self.node_tree.interface).items_tree
            if isinstance(item, bpy.types.NodeTreeInterfaceSocket) and item.in_out == "INPUT" and hasattr(item, "default_value")
        }


    def get_socket_renames(self, saved: dict[str, SavedSocket]) -> dict[str, str]:
        """Old socket name -> new socket name, for values and links to follow a major update."""
        return {}


    def update_node_group_mayor(self) -> list[str]:
        """Swaps in the current group, carries links, values and hidden state over by socket name, returns what got lost."""
        tree = cast(bpy.types.ShaderNodeTree, self.id_data)
        old_defaults = self.get_interface_defaults()
        inputs = {socket.name: SavedSocket.save(socket, [not_none(link.from_socket) for link in not_none(socket.links)], old_defaults.get(socket.identifier)) for socket in self.inputs}
        outputs = {socket.name: SavedSocket.save(socket, [not_none(link.to_socket) for link in not_none(socket.links)]) for socket in self.outputs}
        renames = self.get_socket_renames(inputs)

        # identifiers can survive the swap on a different socket, start clean and restore by name only
        for socket in (*self.inputs, *self.outputs):
            for link in list(not_none(socket.links)): tree.links.remove(link)

        self.node_tree = self.get_node_group()
        defaults = self.get_interface_defaults()
        for socket in self.inputs:
            if socket.identifier in defaults: butils.set_default_value(socket, defaults[socket.identifier])
        self.apply_socket_data()

        lost: list[str] = []
        for name, saved in inputs.items():
            new_name = renames.get(name, name)
            if new_name not in self.inputs:
                if saved.links or saved.changed: lost.append(f"Input '{name}' removed")
                continue
            socket = self.inputs[new_name]
            if not saved.restore(socket, lambda other: tree.links.new(other, socket)): lost.append(f"Input '{name}' value doesn't fit '{new_name}'")
        for name, saved in outputs.items():
            new_name = renames.get(name, name)
            if new_name not in self.outputs:
                if saved.links: lost.append(f"Output '{name}' removed")
                continue
            socket = self.outputs[new_name]
            saved.restore(socket, lambda other: tree.links.new(socket, other))
        # after restoring, so it sees the carried over values
        self.post_init()
        return lost


    def update(self) -> None:
        runtime = self.runtime
        if runtime.updating: return
        runtime.updating = True
        try: self.single_update()
        finally: runtime.updating = False


    def single_update(self):
        """Called from update, sockets can be changed here without updating the node again. Change links in deferred_update."""


    def defer_update(self) -> None:
        """Runs deferred_update once the current operator is done. Links changed inside update, while dragging a link in the
        editor, can stay or keep their sockets flagged as linked (which then can't be hidden)."""
        _DEFERRED_UPDATES[self.as_pointer()] = cast(bpy.types.NodeTree, self.id_data)
        if not bpy.app.timers.is_registered(apply_deferred_updates): bpy.app.timers.register(apply_deferred_updates)


    def deferred_update(self) -> None:
        """Called after defer_update outside of the tree update, links can be changed here without updating the node again."""


    def draw_buttons(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        if self.is_node_group_mayor_outdated:
            row = layout.row()
            row.alert = True
            row.context_pointer_set("node", self)
            row.operator(OT_UpdateNodeGroup.bl_idname, text=f"Update v{self.node_tree_version[0]} > v{self.ng_version_mayor}", icon="FILE_REFRESH")

        messages = self.runtime.messages
        if len(messages) > 0:
            col = layout.column()
            col.scale_y = 0.8
            col.alert = True
            for msg in messages:
                col.label(text=msg)


    def get_node_group_name(self):
        return f".{self.bl_idname}_v{self.ng_version_mayor}"

    
    def find_node_group(self) -> bpy.types.ShaderNodeTree | None:
        """The existing group to share, may be minor outdated."""
        # the stubs type every group as a ShaderNodeTree
        group = cast(bpy.types.NodeTree | None, bpy.data.node_groups.get(self.get_node_group_name()))
        if group is not None and not isinstance(group, bpy.types.ShaderNodeTree): raise Exception()
        return group


    def is_node_group_current(self, group: bpy.types.NodeTree) -> bool:
        return group.get(NODE_GROUP_VERSION_MINOR_KEY, -1) >= self.ng_version_minor


    def get_node_group(self):
        group_name = self.get_node_group_name()

        group = self.find_node_group() if self.ng_shared else None
        if group is not None:
            if self.is_node_group_current(group): return group
            # outdated, step aside so the fresh group gets the name, update_node_groups moves the users over
            if not group.name.endswith("_outdated"): group.name = f"{group_name}_outdated"

        ngb = _Extended_NGB(group_name)
        self.create_node_group(ngb)
        ngb.finish()
        ngb.arrange_nodes()
        tree = ngb.tree
        tree.color_tag = self.ng_color_tag # pyright: ignore[reportAttributeAccessIssue]
        text = ngb.ngdata.dump()
        _NODE_GROUP_DATA_RUNTIME_DICT[text] = ngb.ngdata
        tree[NODE_GROUP_JSON_KEY] = text
        tree[NODE_GROUP_VERSION_MAYOR_KEY] = self.ng_version_mayor
        tree[NODE_GROUP_VERSION_MINOR_KEY] = self.ng_version_minor

        return tree


    def create_node_group(self, ngb: _Extended_NGB):
        pass



class ImageType(StrEnum):
    NONE = "None"
    COLOR_RGBA = "RGBA"
    COLOR_RGB = "RGB"
    NORMAL = "Normal"
    DATA = "Data"


    @staticmethod
    def for_socket(socket: types.NodeSocket) -> ImageType | None:
        """The image output a socket expects, None for sockets an image doesn't go into."""
        return _SOCKET_IMAGE_TYPES.get(socket.type)


_SOCKET_IMAGE_TYPES: dict[str, ImageType] = {
    'BUNDLE': ImageType.COLOR_RGBA,
    'RGBA': ImageType.COLOR_RGB,
    'VECTOR': ImageType.NORMAL,
    'VALUE': ImageType.DATA,
}


class _BeamImageTexIO_Sockets(StrEnum):
    STRENGTH = SocketName.Strength
    COLOR_RGBA = ImageType.COLOR_RGBA
    COLOR_RGB = ImageType.COLOR_RGB
    NORMAL = ImageType.NORMAL
    DATA = ImageType.DATA


        
class _BeamImageTexIO(BaseShaderNode):

    image_type: ImageType 


    def draw_buttons(self, context: Context, layout: UILayout):
        super().draw_buttons(context, layout)
        self.draw_buttons_top(layout)
        layout.prop(self, "image_type")


    def draw_buttons_top(self, layout: UILayout):...


    def single_update(self):
        if self.node_tree is not None: self.defer_update()


    def deferred_update(self):
        # still being created, or an outdated group with the old socket names
        if self.node_tree is None or self.is_node_group_mayor_outdated: return
        # None shows every output and leaves the choice to the user
        if self.image_type != ImageType.NONE: self.follow_links()
        # hides outputs again once their link is gone
        self.post_init()


    def follow_links(self):
        """Moves each link to the output its target socket expects, the type follows the last moved link."""
        tree = cast(bpy.types.NodeTree, self.id_data)
        image_type: ImageType | None = None
        for output in self.outputs:
            for link in list(not_none(output.links)):
                to_socket = not_none(link.to_socket)
                wanted = ImageType.for_socket(to_socket)
                if wanted is None or wanted == output.name or wanted not in self.outputs: continue
                muted = link.is_muted
                tree.links.remove(link)
                tree.links.new(self.outputs[wanted], to_socket).is_muted = muted
                image_type = wanted
        if image_type is not None and image_type != self.image_type: self.image_type = image_type


    def post_init(self):
        def hide(socket: types.NodeSocket, type: ImageType): 
            socket.hide = not(self.image_type == type or self.image_type == ImageType.NONE)
        LS = _BeamImageTexIO_Sockets
        hide(self.inputs[LS.STRENGTH], ImageType.NORMAL)
        hide(self.outputs[LS.COLOR_RGBA], ImageType.COLOR_RGBA)
        hide(self.outputs[LS.COLOR_RGB], ImageType.COLOR_RGB)
        hide(self.outputs[LS.NORMAL], ImageType.NORMAL)
        hide(self.outputs[LS.DATA], ImageType.DATA)

_BeamImageTexIO.annotate(
    image_type = ImageType.to_bpy_enum("Type", default=ImageType.COLOR_RGB, update=_BaseShaderNode_post_init)
)


class BeamImageTexConverter(_BeamImageTexIO):
    bl_idname = f"{SHADER_NODE_PREFIX}TexImgConverter"
    bl_label = "BNG Image Converter"
    ng_color_tag = GroupColorTag.CONVERTER


    class Sockets(StrEnum):
        COLOR = SocketName.Color
        ALPHA = SocketName.Alpha
        STRENGTH = _BeamImageTexIO_Sockets.STRENGTH
        COLOR_RGBA = _BeamImageTexIO_Sockets.COLOR_RGBA
        COLOR_RGB = _BeamImageTexIO_Sockets.COLOR_RGB
        NORMAL = _BeamImageTexIO_Sockets.NORMAL
        DATA = _BeamImageTexIO_Sockets.DATA


    def create_node_group(self, ngb):
        LS = BeamImageTexConverter.Sockets

        in_color = ngb.input(_COLOR_TEXTURE, LS.COLOR, COLOR_WHITE)
        in_alpha = ngb.input(_FLOAT_TEXTURE, LS.ALPHA, 1)
        in_strength = ngb.input(_FLOAT_VALUE, LS.STRENGTH, 1)

        out_rgb = ngb.output(_COLOR_TEXTURE, LS.COLOR_RGB)
        out_rgba = ngb.output(_RGBA_TEXTURE, LS.COLOR_RGBA)
        out_normal = ngb.output(_NORMAL_TEXTURE, LS.NORMAL)
        out_data = ngb.output(_FLOAT_TEXTURE, LS.DATA)

        in_color >> out_rgb
        ngb.RGBA_combine(in_color, in_alpha) >> out_rgba
        ngb.nc.node(types.ShaderNodeSeparateXYZ, in_color)[0] >> out_data

        normal_map = ngb.nc.node(bpy.types.ShaderNodeNormalMap)
        in_strength >> normal_map[SocketName.Strength]
        in_color >> normal_map[SocketName.Color]
        normal_map[SocketName.Normal] >> out_normal



class BeamImageTex(_BeamImageTexIO):

    bl_idname = f"{SHADER_NODE_PREFIX}TexImg"
    bl_label = "BNG Image Texture"
    bl_width_default = 240
    ng_color_tag = GroupColorTag.TEXTURE

 
    class Sockets(StrEnum):
        UV = SocketName.Vector
        STRENGTH = _BeamImageTexIO_Sockets.STRENGTH
        COLOR_RGBA = _BeamImageTexIO_Sockets.COLOR_RGBA
        COLOR_RGB = _BeamImageTexIO_Sockets.COLOR_RGB
        NORMAL = _BeamImageTexIO_Sockets.NORMAL
        DATA = _BeamImageTexIO_Sockets.DATA


    image: bpy.types.Image | None


    def get_node_group_name(self):
        # only for reading, Blender 4.5 cuts names at 63 bytes and images get renamed, find_node_group matches the image
        base_name = super().get_node_group_name()
        return base_name if self.image is None else f"{base_name}_{self.image.name_full}"


    def find_node_group(self) -> bpy.types.ShaderNodeTree | None:
        """The group holding this node's image, a current one first."""
        prefix = super().get_node_group_name()
        found: list[bpy.types.ShaderNodeTree] = []
        for group in bpy.data.node_groups:
            if not isinstance(group, bpy.types.ShaderNodeTree) or not group.name.startswith(prefix): continue
            if group.get(NODE_GROUP_VERSION_MAYOR_KEY) != self.ng_version_mayor: continue
            images = [node.image for node in group.nodes if isinstance(node, bpy.types.ShaderNodeTexImage)]
            if images == [self.image]: found.append(group)
        return next((group for group in found if self.is_node_group_current(group)), found[0] if found else None)


    def create_node_group(self, ngb):

        LS = BeamImageTex.Sockets
        CS = BeamImageTexConverter.Sockets

        in_uv = ngb.input(_UV_NODE, SocketName.Vector)
        in_strength = ngb.input(_FLOAT_VALUE, SocketName.Strength)

        out_rgb = ngb.output(_COLOR_TEXTURE, LS.COLOR_RGB)
        out_rgba = ngb.output(_RGBA_TEXTURE, LS.COLOR_RGBA)
        out_normal = ngb.output(_NORMAL_TEXTURE, LS.NORMAL)
        out_data = ngb.output(_FLOAT_TEXTURE, LS.DATA)

        imgtex = ngb.nc.node(bpy.types.ShaderNodeTexImage, image = self.image)
        converter = ngb.nc.node(BeamImageTexConverter)

        imgtex[SocketName.Color] >> converter[CS.COLOR]
        imgtex[SocketName.Alpha] >> converter[CS.ALPHA]
        in_strength >> converter[CS.STRENGTH]
        in_uv >> imgtex[SocketName.Vector]

        converter[CS.COLOR_RGB] >> out_rgb
        converter[CS.COLOR_RGBA] >> out_rgba
        converter[CS.NORMAL] >> out_normal
        converter[CS.DATA] >> out_data


    def draw_buttons_top(self, layout):
        layout.template_ID(self, "image", open="image.open", new="image.new")

BeamImageTex.annotate(
    image = props.PointerProperty(name="Image", type=bpy.types.Image, update=_BaseShaderNode_init)
)



class BeamFactorColor(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}FactorColor"
    bl_label = "BNG Factor (Color)"
    bl_nclass = "OP_COLOR"
    ng_color_tag = GroupColorTag.COLOR


    def create_node_group(self, ngb: NodeGroupBuilder):
        
        texture = ngb.input(_COLOR_TEXTURE, SocketName.TextureMap)
        factor = ngb.input(_COLOR_VALUE, SocketName.Factor)

        result = ngb.output(_COLOR, "Result")

        ngb.panel("Advanced")
        vc = ngb.input(_COLOR_VALUE, SocketName.VertexColor)
        ic = ngb.input(_COLOR_VALUE, SocketName.InstanceColor)

        texture * factor * vc * ic >> result


        
class BeamFactorFloat(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}FactorFloat"
    bl_label = "BNG Factor (Data)"
    bl_nclass = "CONVERTER"
    ng_color_tag = GroupColorTag.CONVERTER


    def create_node_group(self, ngb: NodeGroupBuilder):
        ngb.input(_FLOAT_TEXTURE, SocketName.TextureMap) * ngb.input(_FLOAT_VALUE, SocketName.Factor) >> ngb.output(_FLOAT, "Result")



class BeamUVData(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}UVData"
    bl_label = "BNG UV"
    ng_color_tag = GroupColorTag.VECTOR

    class Sockets(StrEnum):
        UV0 = "UV 0"
        UV1 = "UV 1"
        ANIMATION = "Animation"
        DETAIL_SCALE = "Detail Scale"
        DETAIL_UV0 = "Detail UV 0"
        DETAIL_UV1 = "Detail UV 1"


    def create_node_group(self, ngb):

        INVALID = -1e20
        INVALID_VEC = (0, 0, INVALID)

        def seperate_xyz(src: LinkSource): return ngb.nc.node(bpy.types.ShaderNodeSeparateXYZ, src)
        def combine_xyz(x: LinkSource, y: LinkSource, z: LinkSource): return ngb.nc.node(bpy.types.ShaderNodeCombineXYZ, x, y, z)

        LS = BeamUVData.Sockets
        
        in_uv0 = ngb.input(_UV_NODE, LS.UV0, INVALID_VEC)
        in_uv1 = ngb.input(_UV_NODE, LS.UV1, INVALID_VEC)
        out_uv0 = ngb.output(_UV_NODE, LS.UV0)
        out_uv1 = ngb.output(_UV_NODE, LS.UV1)
        anim_bundle = ngb.input(_BUNDLE_NODE, LS.ANIMATION)

        ngb.panel("Detail")
        detail_scale = ngb.input(_VEC2_VALUE, LS.DETAIL_SCALE, (1,1,1))
        out_detail_uv0 = ngb.output(_UV_NODE, LS.DETAIL_UV0)
        out_detail_uv1 = ngb.output(_UV_NODE, LS.DETAIL_UV1)

        default_uv = ngb.nc.node(bpy.types.ShaderNodeUVMap)

        uv0_z = seperate_xyz(in_uv0)[2]
        uv0_is_invalid = ngb.nc.compare(uv0_z, INVALID)

        uv0 = in_uv0.mix(default_uv, uv0_is_invalid)
        uv1 = in_uv1

        anim_split = ngb.nc.seperate_bundle(UVMATRIX, anim_bundle)
        anim_enabled = anim_split[SocketName.Enabled]
        anim_matrix = (
            seperate_xyz(anim_split["U"]), 
            seperate_xyz(anim_split["V"])
        )

        def apply_matrix(uv: LinkSource):
            xy = seperate_xyz(uv)
            new_x = xy[0] * anim_matrix[0][0] + xy[1] * anim_matrix[0][1] + anim_matrix[0][2]
            new_y = xy[0] * anim_matrix[1][0] + xy[1] * anim_matrix[1][1] + anim_matrix[1][2]
            xy = combine_xyz(new_x, new_y, xy[2])
            return ngb.nc.mix(anim_enabled, uv, xy)

        uv0 = apply_matrix(uv0)
        uv1 = apply_matrix(uv1)

        uv0 >> out_uv0
        uv1 >> out_uv1

        uv0 * detail_scale >> out_detail_uv0
        uv1 * detail_scale >> out_detail_uv1

        

class BeamUVAnimation(BaseShaderNode):

    """
    Torque3D texture animation (ProcessedShaderMaterial::_setTextureTransforms, GarageGames version BeamNG forked from).
    Motion picks Scroll or Rotate (rotation replaces scroll), modifiers map to their animFlags bit:
    a Wave Type drives the motion instead of its speed, Scale pulses with the wave and fits one frame with Sequence.
    """

    bl_idname = f"{SHADER_NODE_PREFIX}UVAnimation"
    bl_label = "BNG UV Animation"
    ng_color_tag = GroupColorTag.VECTOR
    ng_version_mayor = 5


    class Sockets(StrEnum):
        UV = "UV"
        ANIMATION = "Animation"
        MOTION = "Motion"
        SCALE = "Scale"
        MOTION_PIVOT_OFFSET = "Motion Pivot Offset"
        MOTION_SPEED = "Motion Speed"
        MOTION_DIRECTION = "Motion Direction"
        WAVE_TYPE = "Wave Type"
        WAVE_AMPLITUDE = "Amplitude"
        WAVE_FREQUENCY = "Frequency"
        SEQUENCE = "Sequence"
        FRAMES_SEC = "Frames/Sec"
        FRAMES = "Frames"
        TIME_SOURCE = "Time"
        SECONDS = "Seconds"


    class Motion(StrEnum):
        NONE = "None"
        SCROLL = "Scroll"
        ROTATE = "Rotate"


    class WaveType(StrEnum):
        NONE = "None"
        SIN = "Sin"
        SQUARE = "Square"
        TRIANGLE = "Triangle"


    class TimeSource(StrEnum):
        SCENE = "Scene Time"
        VALUE = "Value"


    def get_socket_renames(self, saved: dict[str, SavedSocket]):
        LS = BeamUVAnimation.Sockets
        # v4, scroll and rotation got shared sockets, take the speed the motion used
        motion = saved.get(LS.MOTION)
        rotate = motion is not None and motion.value == BeamUVAnimation.Motion.ROTATE
        return {
            "Scroll Factor": LS.MOTION_DIRECTION.value,
            "Rotation Pivot Offset": LS.MOTION_PIVOT_OFFSET.value,
            "Rotation Speed" if rotate else "Scroll Speed": LS.MOTION_SPEED.value,
            "Wave Amplitude": LS.WAVE_AMPLITUDE.value,
            "Wave Frequency": LS.WAVE_FREQUENCY.value,
        }


    def create_node_group(self, ngb: NodeGroupBuilder):

        def op(operation: Operation, value: LinkSource): return ngb.nc.math(operation, value)
        def seperate_xyz(src: LinkSource): return ngb.nc.node(bpy.types.ShaderNodeSeparateXYZ, src)
        def combine_xyz(x: LinkSource, y: LinkSource, z: LinkSource = 0.0): return ngb.nc.node(bpy.types.ShaderNodeCombineXYZ, x, y, z)

        LS = BeamUVAnimation.Sockets
        WT = BeamUVAnimation.WaveType
        TAU = 6.283185307179586
        CENTER = (0.5, 0.5, 0.0)

        time_source_input = ngb.input(_MENU, LS.TIME_SOURCE, BeamUVAnimation.TimeSource.SCENE)
        time_source_value = ngb.input(_FLOAT_ANY_VALUE, LS.SECONDS)

        output = ngb.output(_BUNDLE_NODE, LS.ANIMATION)

        ngb.panel("Motion")
        motion_input = ngb.input(_MENU, LS.MOTION, BeamUVAnimation.Motion.NONE)
        motion_direction = ngb.input(_VEC2_VALUE, LS.MOTION_DIRECTION)
        motion_pivot = ngb.input(_VEC2_VALUE, LS.MOTION_PIVOT_OFFSET)
        motion_speed = ngb.input(_FLOAT_ANY_VALUE, LS.MOTION_SPEED)

        ngb.panel("Modifiers")
        wave_type = ngb.input(_MENU, LS.WAVE_TYPE, WT.NONE)
        wave_amp = ngb.input(_FLOAT_ANY_VALUE, LS.WAVE_AMPLITUDE)
        wave_freq = ngb.input(_FLOAT_ANY_VALUE, LS.WAVE_FREQUENCY)
        scale = ngb.input(_BOOL_VALUE, LS.SCALE)
        sequence = ngb.input(_BOOL_VALUE, LS.SEQUENCE)
        fps = ngb.input(_FLOAT_ANY_VALUE, LS.FRAMES_SEC)
        frames = ngb.input(_FLOAT_ANY_VALUE, LS.FRAMES)

        motion = ngb.nc.menu_switch(SocketType.Float, *BeamUVAnimation.Motion, menu=motion_input)
        for index, item in enumerate(BeamUVAnimation.Motion): index >> motion[item]
        scroll = ngb.nc.compare(motion, 1)
        rotate = ngb.nc.compare(motion, 2)

        # a menu socket can only drive one Menu Switch, switch on its index
        wave_index = ngb.nc.menu_switch(SocketType.Float, *WT, menu=wave_type)
        for index, item in enumerate(WT): index >> wave_index[item]
        wave = wave_index > 0

        seconds = ngb.nc.menu_switch(SocketType.Float, *BeamUVAnimation.TimeSource, menu=time_source_input)
        ngb.nc.node(bpy.types.GeometryNodeInputSceneTime)[LS.SECONDS] >> seconds[BeamUVAnimation.TimeSource.SCENE]
        time_source_value >> seconds[BeamUVAnimation.TimeSource.VALUE]

        # wave offset (_getWaveOffset), phase wrapped for precision, all wave types are periodic
        phase = op(Operation.FRACT, wave_freq * seconds)
        phase_4 = phase * 4
        sine = op(Operation.SINE, phase * TAU)
        triangle = phase_4.mix(2 - phase_4, phase > 0.25).mix(phase_4 - 4, phase > 0.75)
        square = (phase > 0.5) | (phase < 1e-6)
        waves = sine.mix(triangle, ngb.nc.compare(wave_index, list(WT).index(WT.TRIANGLE)))
        waves = waves.mix(square, ngb.nc.compare(wave_index, list(WT).index(WT.SQUARE)))
        wave_offset = ngb.nc.mix(wave, 0.0, waves * wave_amp)

        # texture matrix in torque UV space, 2x3 affine as columns: u' = col_u * u + col_v * v + trans

        # scroll (sets the translation)
        scroll_offset = (motion_direction * (motion_speed * seconds)).mix(motion_direction * wave_offset, wave)
        trans = ngb.nc.mix(scroll, (0.0, 0.0, 0.0), scroll_offset)  # mix instead of multiply, so unused inputs are greyed out

        # rotation (replaces the matrix, scroll is lost): R * (uv + pivot) + 0.5, R = [cos sin; -sin cos]
        angle = (motion_speed * seconds).mix(wave_offset * TAU, wave)
        cos, sin = op(Operation.COSINE, angle), op(Operation.SINE, angle)
        rot_u = combine_xyz(cos, -sin)
        rot_v = combine_xyz(sin, cos)
        motion_pivot = seperate_xyz(motion_pivot)
        col_u = ngb.nc.mix(rotate, (1.0, 0.0, 0.0), rot_u)
        col_v = ngb.nc.mix(rotate, (0.0, 1.0, 0.0), rot_v)
        trans = trans.mix(rot_u * motion_pivot[0] + rot_v * motion_pivot[1] + CENTER, rotate)

        # scale + wave: translation reset to the center, then scaled by |wave| around it
        w = ngb.nc.abs(wave_offset)
        wave_scale = scale * wave
        trans = trans.mix((col_u + col_v) * (w * -0.5) + CENTER, wave_scale)
        col_u = col_u.mix(col_u * w, wave_scale)
        col_v = col_v.mix(col_v * w, wave_scale)

        # image sequence: u offset by whole frames, scale shrinks u to one frame
        segment = 1 / frames
        col_u = col_u.mix(col_u * segment, sequence * scale)
        trans = trans.mix(trans + combine_xyz(op(Operation.FLOOR, seconds * fps) * segment, 0.0), sequence)

        # to blender UV space (v flipped on export): u' = a u - b v + (b + c), v' = -d u + e v + (1 - e - f)
        u, v, t = seperate_xyz(col_u), seperate_xyz(col_v), seperate_xyz(trans)
        a, d, b, e, c, f = u[0], u[1], v[0], v[1], t[0], t[1]
        enabled = (motion > 0) | wave | scale | sequence
        ngb.nc.combine_bundle(UVMATRIX, combine_xyz(a, -b, b + c), combine_xyz(-d, e, 1 - e - f), enabled) >> output



class BeamDetailNormal(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}DetailNormal"
    bl_label = "BNG Detail Normal"
    bl_nclass = "OP_VECTOR"
    ng_color_tag = GroupColorTag.VECTOR


    def create_node_group(self, ngb: NodeGroupBuilder):
        
        base = ngb.nc.node(BeamNormalOrDefault, ngb.input(_NORMAL_MIX, "Base"))
        detail = ngb.nc.node(BeamNormalOrDefault, ngb.input(_NORMAL_MIX, "Detail"))
        neutral = ngb.nc.node(bpy.types.ShaderNodeNormalMap)
        (base + (neutral - detail)) >> ngb.output(_NORMAL_MIX, "Normal")



class BeamBSDFCollision(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BSDFCollision"
    bl_label = "BNGS Collision"
    bl_icon = 'MOD_PHYSICS'
    bl_nclass = "SHADER"
    bl_width_default = 200
    ng_color_tag = GroupColorTag.SHADER
    ng_version_minor = 1


    def create_node_group(self, ngb):
        display_enabled = ngb.input(_BOOL_DISPLAY, "Display", default_value=True)
        display_color = ngb.input(_COLOR_DISPLAY, "Color", default_value=COLOR_MAGENTA)
        output = ngb.output(SocketType.Shader, SocketName.Shader)

        bsdf = ngb.nc.node(types.ShaderNodeBsdfPrincipled)

        display_enabled >> bsdf[SocketName.Alpha]
        display_color >> bsdf[SocketName.BaseColor]
        bsdf >> output



class BeamNormalOrDefault(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}NormalOrDefault"
    bl_label = "NormalOrDefault"
    ng_color_tag = GroupColorTag.INPUT


    def create_node_group(self, ngb):

        value = ngb.input(_NORMAL_MIX, SocketName.Normal)
        
        length = ngb.nc.math(Operation.LENGTH, value)[SocketName.Value]
        is_empty = ngb.nc.math(Operation.COMPARE, length, 0, 0)
        default = ngb.nc.node(bpy.types.ShaderNodeNewGeometry)[SocketName.Normal]

        result = ngb.nc.mix(is_empty, value, default)
        result >> ngb.output(_NORMAL_MIX, SocketName.Normal)



class BeamInvertBackfaceNormal(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}InvertBackfaceNormal"
    bl_label = "Invert Backface Normal"
    ng_color_tag = GroupColorTag.VECTOR


    def create_node_group(self, ngb):

        two_sided = ngb.input(_NORMAL_MIX, SocketName.Normal)
        do_invert = ngb.input(_BOOL_VALUE, SocketName.InvertBackfaceNormals, default_value=True)
        inverse = two_sided * (-1.0,-1.0,-1.0)

        is_backfacing = ngb.nc.node(NodeName.Geometry)[SocketName.Backfacing]
        one_sided = ngb.nc.mix(is_backfacing, two_sided, inverse)

        result = ngb.nc.mix(do_invert, one_sided, two_sided)
        result >> ngb.output(_NORMAL_MIX, SocketName.Normal)



class BeamNormals(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}NormalMap"
    bl_label = "BNG Normal Map"
    ng_color_tag = GroupColorTag.VECTOR


    def create_node_group(self, ngb: NodeGroupBuilder):
        pass



class BaseBeamRGBA(BaseShaderNode):

    color_value: Tuple4F


    @property
    def inputs_rgb(self): return self.inputs["RGB"]


    @property
    def input_a(self): return self.inputs["A"]


    def post_init(self):
        butils.set_default_value(self.inputs_rgb, self.color_value)
        butils.set_default_value(self.input_a, self.color_value[3])
        self.inputs_rgb.hide = True
        self.input_a.hide = True


    def draw_buttons(self, context, layout):
        super().draw_buttons(context, layout)
        layout.prop(self, "color_value", text="")

BaseBeamRGBA.annotate(
    color_value = props.FloatVectorProperty(
        subtype='COLOR', size=4,
        default=(1.0, 1.0, 1.0, 1.0),
        min=0.0, max=1.0,
        update=_BaseShaderNode_post_init
    )
)


class BeamRGBA(BaseBeamRGBA):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Input"
    bl_label = "BNG RGBA"
    ng_color_tag = GroupColorTag.INPUT


    def create_node_group(self, ngb):

        ngb.RGBA_output("RGBA", ngb.input(_COLOR, "RGB"), ngb.input(_FLOAT, "A"))



class BeamRGBAMix(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Mix"
    bl_label = "BNG RGBA Mix"
    ng_color_tag = GroupColorTag.COLOR


    def create_node_group(self, ngb):

        factor = ngb.input(_FLOAT, "Factor")
        
        a = ngb.RGBA_input("A")
        b = ngb.RGBA_input("B")

        color_mix = ngb.nc.mix(factor, a[0], b[0])
        alpha_mix = ngb.nc.mix(factor, a[1], b[1])

        ngb.RGBA_output("Result", color_mix, alpha_mix)



class BeamRGBADefault(BaseBeamRGBA):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Default"
    bl_label = "BNG RGBA Default"
    ng_color_tag = GroupColorTag.INPUT


    def create_node_group(self, ngb):

        value = ngb.input(SocketType.Bundle, "Value")
        default = ngb.RGBA_combine(ngb.input(_COLOR, "RGB"), ngb.input(_FLOAT, "A"))
        factor = ngb.RGBA_seperate(value)[SocketName.Enabled]
        ngb.nc.node(BeamRGBAMix, factor, default, value) >> ngb.output(SocketType.Bundle, "RGBA")



class BeamOperatorNode(BaseShaderNode):

    ng_color_tag = GroupColorTag.CONVERTER

    @classmethod
    def mix(cls, a: LinkBuilderBase, b: LinkSource, i: int = 0):
        return a.ntb.nc.node(cls, a, b)


    @classmethod
    def mix_xyz(cls, a: LinkBuilderBase, b: LinkSource):
        return a.ntb.nc.mix_foreach_xyz(a, b, cls.mix)



class BeamONHardLight(BeamOperatorNode):

    bl_idname = f"{SHADER_NODE_PREFIX}MathHardLight"
    bl_label = "BNG HardLight"

    def create_node_group(self, ngb: NodeGroupBuilder):

        i = ngb.input(_FLOAT_VALUE, "I")
        m = ngb.input(_FLOAT_VALUE, "M")

        dark = 2 * i * m
        light = 1 - (2 * (1 - m) * (1 - i))

        dark.mix(light, m > 0.5) >> ngb.output(_FLOAT_VALUE, SocketName.Value)



_OPERATOR_NODES: SDict[type[BeamOperatorNode]] = {
    Operation.HARD_LIGHT: BeamONHardLight
}



class BeamRGBAMath(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Math"
    bl_label = "BNG RGBA Math"
    ng_color_tag = GroupColorTag.COLOR


    operation: str


    def get_node_group_name(self):
        return f"{super().get_node_group_name()}_{self.operation}"


    def create_node_group_body(self, a: LinkBuilderBase, b: LinkBuilderBase):
        ngb = a.ntb

        if self.operation == Operation.OVERLAY:
            return ngb.nc.mix(b[1], a[0], b[0]), a[1]

        op_cls = _OPERATOR_NODES.get(self.operation)
        if op_cls is not None:
            return op_cls.mix_xyz(a[0], b[0]), op_cls.mix(a[1], b[1])

        return ngb.nc.math(self.operation, a[0], b[0]), ngb.nc.math(self.operation, a[1], b[1]) 


    def create_node_group(self, ngb):

        a = ngb.RGBA_input("A")
        b = ngb.RGBA_input("B", Vec4F.from_value(Operation(self.operation).neutral_value))
        ngb.RGBA_output("Result", *self.create_node_group_body(a, b))


    def draw_buttons(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        super().draw_buttons(context, layout)
        layout.prop(self, "operation", text="")


BeamRGBAMath.__annotations__.update(
    operation = Operation.to_bpy_enum("Type", default=Operation.MULTIPLY, update=_BaseShaderNode_init)
)



class BeamPaletteEval(BaseShaderNode):
    
    bl_idname = f"{SHADER_NODE_PREFIX}PaletteEval"
    bl_label = "BNG Eval Palette"
    ng_color_tag = GroupColorTag.CONVERTER

    def create_node_group(self, ngb):

        pallete_bundle = ngb.input(_BUNDLE_NODE, "Palette")
        pallete = ngb.nc.seperate_bundle(PAINT_LAYER, pallete_bundle)
        enabled = pallete[SocketName.Enabled]
        enabled >> ngb.output(SocketType.Bool, SocketName.Enabled)

        def socket(name: str, socket_type = SocketType.Float, default: SocketValue = 1):
            ngb.nc.mix(enabled, default, pallete[name]) >> ngb.output(socket_type, name)

        socket(SocketName.Color, SocketType.Color, COLOR_WHITE)
        socket(SocketName.Alpha)
        socket(SocketName.Metallic)
        socket(SocketName.Roughness)
        socket(SocketName.ClearCoat)
        socket(SocketName.ClearCoatRoughness)



class BeamPalette(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}Palette"
    bl_label = "BNG Palette"
    ng_color_tag = GroupColorTag.CONVERTER


    class Sockets(StrEnum):
        PALETTE_MAP = "Palette Map"
        COLOR = SocketName.Color
        METALLIC = SocketName.Metallic
        ROUGHNESS = SocketName.Roughness
        CLEAR_COAT = SocketName.ClearCoat
        CLEAR_COAT_ROUGHNESS = SocketName.ClearCoatRoughness
        PALETTE = "Palette"


    def create_node_group(self, ngb):

        LS = BeamPalette.Sockets

        pmap = ngb.input(_COLOR_TEXTURE, LS.PALETTE_MAP, COLOR_RED)
        color_enabled = ngb.input(_BOOL_VALUE, LS.COLOR, True)
        metallic_enabled = ngb.input(_BOOL_VALUE, LS.METALLIC, True)
        roughness_enabled = ngb.input(_BOOL_VALUE, LS.ROUGHNESS, True)
        cc_enabled = ngb.input(_BOOL_VALUE, LS.CLEAR_COAT, True)
        ccr_enabled = ngb.input(_BOOL_VALUE, LS.CLEAR_COAT_ROUGHNESS, True)
        paint_bundle = ngb.input(_BUNDLE_DISPLAY, "Paint")

        layers_bundle = ngb.nc.seperate_bundle(PAINT3, paint_bundle)
        def sep_layer(index: int): return ngb.nc.seperate_bundle(PAINT_LAYER, layers_bundle[index])
        layers = sep_layer(0), sep_layer(1), sep_layer(2)
        factor = ngb.nc.node(bpy.types.ShaderNodeSeparateXYZ, ngb.nc.math(Operation.NORMALIZE, pmap))

        result = ngb.nc.combine_bundle(PAINT_LAYER)
        result[SocketName.Enabled] << True

        def mix3(name: str, enabled: LinkSource, default: SocketValue = 1):
            def mix(index: int): 
                layer = layers[index]
                return factor[index] * ngb.nc.mix(layer[SocketName.Enabled], default, layer[name])
            mix_value = mix(0) + mix(1) + mix(2)
            ngb.nc.mix(enabled, default, mix_value) >> result[name]

        mix3(SocketName.Color, color_enabled, COLOR_WHITE)
        mix3(SocketName.Alpha, color_enabled)
        mix3(SocketName.Metallic, metallic_enabled)
        mix3(SocketName.Roughness, roughness_enabled)
        mix3(SocketName.ClearCoat, cc_enabled)
        mix3(SocketName.ClearCoatRoughness, ccr_enabled)

        result >> ngb.output(_BUNDLE_NODE, LS.PALETTE)



class BeamPaint(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}Paint"
    bl_label = "BNG Paint"
    ng_color_tag = GroupColorTag.INPUT

    def create_node_group(self, ngb):
        output = ngb.output(_BUNDLE_DISPLAY, "Paint")
        def new_layer(index: int):
            panel_name = f"Layer {index}"
            ngb.panel(panel_name)
            def new_input(info: _SCI, name: str): return ngb.input(info, f"{panel_name} {name}")
            inputs = (
                new_input(_COLOR_DISPLAY, SocketName.Color),
                new_input(_FLOAT_DISPLAY, SocketName.Alpha),
                new_input(_FLOAT_DISPLAY, SocketName.Metallic),
                new_input(_FLOAT_DISPLAY, SocketName.Roughness),
                new_input(_FLOAT_DISPLAY, SocketName.ClearCoat),
                new_input(_FLOAT_DISPLAY, SocketName.ClearCoatRoughness),
            )
            return ngb.nc.combine_bundle(PAINT_LAYER, *inputs, True)
        ngb.nc.combine_bundle(PAINT3, new_layer(1), new_layer(2), new_layer(3)) >> output



class BeamDisplayInject(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}DisplayInject"
    bl_label = "BNGS Display Inject"
    ng_color_tag = GroupColorTag.SHADER


    class Sockets(StrEnum):
        PAINT = "Paint"
        VERTEX = "Vertex RGBA"
        AO_STRENGTH = SocketName.AmbientOcclusionStrength


    def create_node_group(self, ngb):

        LS = BeamDisplayInject.Sockets

        input = ngb.input(SocketType.Closure, SocketName.BNGShader)
        output = ngb.output(SocketType.Closure, SocketName.BNGShader)

        paint = ngb.input(_BUNDLE_DISPLAY, LS.PAINT)
        vtx_color = ngb.input(_BUNDLE_DISPLAY, LS.VERTEX)
        ao_strength = ngb.input(_FLOAT_DISPLAY, SocketName.AmbientOcclusionStrength, 0.5)

        display_info = ngb.nc.combine_bundle(DISPLAY_INFO, paint, vtx_color, ao_strength)

        closure = ngb.nc.closure(BNGS_IO)
        eval = ngb.nc.eval_closure(BNGS_IO, input)

        BNGS_INPUT.forward(closure, eval, exclude=(SocketName.DisplayInfo,))
        display_info >> eval[SocketName.DisplayInfo]
        BNGS_OUTPUT.forward(eval, closure)
        closure.output >> output



class BeamBDSF10Basic(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BSDF10Basic"
    bl_label = "BNGS 1.0"
    bl_icon = 'SHADERFX'
    bl_nclass = "SHADER"
    bl_width_default = 240
    ng_color_tag = GroupColorTag.SHADER


    class Sockets(StrEnum):
        COLOR_MAP = "RGBA Color Map"
        COLOR_FACTOR = "RGBA Color"
        OVERLAY_MAP = "RGBA Overlay Map"
        PALETTE = "Palette"
        SPECULAR_MAP = "Specular Map"
        SPECULAR_ENABLED = "Specular Enabled"
        SPECULAR_COLOR = "Specular Color"
        SPECULAR_ROUGHNESS = "Specular Roughness"
        RM = "RGBA Reflectivity Map"
        RM_FACTOR = "Reflectivity Map Factor"
        RM_ENABLED = "Reflectivity Map Enabled"
        OPACITY_MAP = "Opacity Map"
        DETAIL_COLOR = "Detail RGBA Color Map"
        EMISIVE = SocketName.Emissive
        GLOW_COLOR = "Glow Color"

        
    #def update(self):
        #LS = BeamBDSF10Basic.Sockets
        #rm_enabled: bpy.types.NodeSocketBool = self.inputs[LS.RM_ENABLED]
        #rm_enabled.default_value = self.inputs[LS.RM].is_linked
        #rm_enabled.hide = False


    def create_node_group(self, ngb):

        def rgba_math(a: LinkSource, b: LinkSource, operation = Operation.MULTIPLY): return ngb.nc.node(BeamRGBAMath, a, b, operation = operation)
        def rgba_mix(factor: LinkSource, a: LinkSource, b: LinkSource): return ngb.nc.node(BeamRGBAMix, factor, a, b)
        LS = BeamBDSF10Basic.Sockets

        # io
        in_rgba_cm = ngb.input(_RGBA_TEXTURE, LS.COLOR_MAP)
        in_rgba_cf = ngb.input(_RGBA_VALUE, LS.COLOR_FACTOR)
        in_ic_enabled = ngb.input(_BOOL_VALUE, SocketName.InstanceColor) 
        in_vc_enabled = ngb.input(_BOOL_VALUE, SocketName.VertexColor) 
        in_normal_map = ngb.input(_NORMAL_TEXTURE, SocketName.Normal)
        out_result = ngb.output(SocketType.Closure, SocketName.BNGShader)

        ngb.panel("Detail")
        in_detail_color = ngb.input(_RGBA_TEXTURE, LS.DETAIL_COLOR)
        in_detail_normal = ngb.input(_NORMAL_MIX, SocketName.DetailNormal)

        ngb.panel("Advanced")
        rgba_rm = ngb.input(_RGBA_TEXTURE, LS.RM)
        rm_factor = ngb.input(_FLOAT_VALUE, LS.RM_FACTOR)
        overlay = ngb.input(_RGBA_TEXTURE, LS.OVERLAY_MAP)
        pallete_bundle = ngb.input(_BUNDLE_NODE, LS.PALETTE)
        opacity_map = ngb.input(_FLOAT_TEXTURE, LS.OPACITY_MAP, default_value=1.0)

        ngb.panel("Lighting")
        in_se = ngb.input(_BOOL_VALUE, LS.SPECULAR_ENABLED, default_value=False)
        in_spec_map = ngb.input(_FLOAT_TEXTURE, LS.SPECULAR_MAP)
        in_sc = ngb.input(_COLOR_VALUE, LS.SPECULAR_COLOR, default_value=COLOR_WHITE)
        in_sr = ngb.input(_FLOAT_VALUE, LS.SPECULAR_ROUGHNESS)
        in_glow_color = ngb.input(_COLOR_VALUE, LS.GLOW_COLOR, default_value=COLOR_BLACK)
        in_emisive = ngb.input(_BOOL_VALUE, LS.EMISIVE)


        closure = ngb.nc.closure(BNGS_IO)
        closure.output >> out_result

        pallete = ngb.nc.node(BeamPaletteEval, pallete_bundle)

        object_info = ngb.nc.node(bpy.types.ShaderNodeObjectInfo)
        vc_info = ngb.nc.node(bpy.types.ShaderNodeVertexColor)

        ic = ngb.RGBA_combine(object_info[SocketName.Color], object_info[SocketName.Alpha])
        vc = ngb.RGBA_combine(vc_info[SocketName.Color], vc_info[SocketName.Alpha])


        rgba = ngb.RGBA_default(in_rgba_cm, COLOR_WHITE)
        rgba = rgba_math(rgba, ngb.RGBA_default(in_detail_color, COLOR_NULL_HALF), Operation.HARD_LIGHT)
        rgba = rgba_math(rgba, in_rgba_cf)
        rgba = rgba_mix(in_ic_enabled & pallete[SocketName.Enabled], rgba, rgba_math(rgba, ic))
        rgba = rgba_mix(in_vc_enabled, rgba, rgba_math(rgba, vc))
        rgba = ngb.nc.node(BeamRGBAMath, rgba, overlay, operation = Operation.OVERLAY)

        normal = ngb.nc.node(BeamInvertBackfaceNormal, ngb.nc.node(BeamDetailNormal, in_normal_map, in_detail_normal), closure[SocketName.InvertBackfaceNormals])

        rgba_bundle = ngb.RGBA_seperate(rgba)
        color = rgba_bundle[SocketName.Color]
        gamma = ngb.nc.node(bpy.types.ShaderNodeGamma, color, 2.2)
        gamma *= pallete[SocketName.Color]
        alpha = rgba_bundle[SocketName.Alpha]
        alpha *= opacity_map
        alpha *= pallete[SocketName.Alpha]
        alpha >> closure[SocketName.Alpha]

        # diffuse
        diffuse = ngb.nc.node(bpy.types.ShaderNodeBsdfDiffuse)
        gamma >> diffuse[SocketName.Color]
        normal >> diffuse[SocketName.Normal]

        # specular
        specular = ngb.nc.node(bpy.types.ShaderNodeEeveeSpecular)
        specular[SocketName.BaseColor] << COLOR_NULL
        spec_color = in_sc * in_spec_map
        spec_color >> specular[SocketName.Specular]
        in_sr >> specular[SocketName.Roughness]
        normal >> specular[SocketName.Normal]

        shader = ngb.nc.mix(in_se, diffuse, diffuse + specular) 

        # emissive
        emssion = ngb.nc.node(bpy.types.ShaderNodeEmission)
        color * (0.5, 0.5, 0.5) >> emssion[SocketName.Color]

        shader = shader.mix(emssion, in_emisive)

        # reflection
        metallic = ngb.nc.node(bpy.types.ShaderNodeBsdfMetallic)
        metallic[SocketName.Roughness] << 0.0
        metallic[SocketName.BaseColor] << COLOR_WHITE
        metallic[SocketName.EdgeTint] << COLOR_WHITE
        normal >> metallic[SocketName.Normal]

        rgba_rm_bundle = ngb.RGBA_seperate(rgba_rm)
        reflectivity = ngb.nc.mix(rgba_rm_bundle[SocketName.Enabled], alpha, rgba_rm_bundle[SocketName.Alpha] * rm_factor) 
        reflectivity *= ngb.nc.bool(closure[SocketName.ReflectionMode])

        shader = shader.mix(metallic, reflectivity)

        #glow
        glow = ngb.nc.node(bpy.types.ShaderNodeEmission)
        in_glow_color >> glow[SocketName.Color]

        shader += glow

        # output
        shader >> closure[SocketName.Shader]
        alpha >> closure[SocketName.Alpha]



class BeamBSDFRetroReflect(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}RetroReflect"
    bl_label = "BNG Retro Reflectivity"
    ng_color_tag = GroupColorTag.VECTOR


    def create_node_group(self, ngb):

        base_color = ngb.input(_COLOR, SocketName.BaseColor)
        rr_color = ngb.input(_COLOR, SocketName.Color)
        rr_factor = ngb.input(_FLOAT, SocketName.Factor)
        metallic = ngb.input(_FLOAT, SocketName.Metallic, 0)
        normal = ngb.input(_NORMAL_MIX, SocketName.Normal)

        bc = ngb.nc.node(bpy.types.ShaderNodeSeparateColor, base_color, mode = "HSV")
        rc = ngb.nc.node(bpy.types.ShaderNodeSeparateColor, rr_color, mode = "HSV")

        h_distance = ngb.nc.abs(bc[0] - rc[0])
        h_distance = h_distance.mix(1 - h_distance, h_distance > 0.5) * 12

        s_distance = ngb.nc.abs(bc[1] - rc[1]) * 2

        factor = (1 - s_distance.clamp()) * ngb.nc.mix(rc[1], 1, 1 - h_distance.clamp())
        strength = (ngb.nc.mix(rc[2] > 0, 1, factor)) * rr_factor * (1 - metallic)

        geometry = ngb.nc.node(bpy.types.ShaderNodeNewGeometry)
        retro_normal = normal - geometry[SocketName.Normal] + geometry["Incoming"]

        normal.mix(retro_normal, strength) >> ngb.output(_NORMAL_MIX, SocketName.Normal)



class BeamBSDF15Detail(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BNGS15Detail"
    bl_label = "BNGS 1.5 Detail"
    bl_width_default = 240
    ng_color_tag = GroupColorTag.SHADER


    class Sockets(StrEnum):
        BASE_COLOR_MAP = "Base Color Map"
        BASE_COLOR_STRENGTH = "Base Color Strength"
        METALLIC_MAP = "Metallic Map"
        METALLIC_STRENGTH = "Metallic Strength"
        NORMAL = "Normal"
        ROUGHNESS_MAP = "Roughness Map"
        ROUGHNESS_STRENGTH = "Roughness Strength"
        OPACITY_MAP = "Opacity Map"
        OPACITY_STRENGTH = "Opacity Strength"
        AO_MAP = "Ambient Occlusion Map"
        AO_STRENGTH = "Ambient Occlusion Strength"


    def create_node_group(self, ngb):
        LS = BeamBSDF15Detail.Sockets

        color_m = ngb.input(_COLOR_TEXTURE, LS.BASE_COLOR_MAP, COLOR_GRAY)
        color_s = ngb.input(_FLOAT_VALUE, LS.BASE_COLOR_STRENGTH)
        normal = ngb.input(_NORMAL_MIX, LS.NORMAL)
        m_m = ngb.input(_FLOAT_TEXTURE, LS.METALLIC_MAP)
        m_s = ngb.input(_FLOAT_VALUE, LS.METALLIC_STRENGTH)
        r_m = ngb.input(_FLOAT_TEXTURE, LS.ROUGHNESS_MAP)
        r_s = ngb.input(_FLOAT_VALUE, LS.ROUGHNESS_STRENGTH)
        o_m = ngb.input(_FLOAT_TEXTURE, LS.OPACITY_MAP)
        o_s = ngb.input(_FLOAT_VALUE, LS.OPACITY_STRENGTH)
        a_m = ngb.input(_FLOAT_TEXTURE, LS.AO_MAP)
        a_s = ngb.input(_FLOAT_VALUE, LS.AO_STRENGTH)

        result = ngb.nc.combine_bundle(DETAIL_LAYER)
        result >> ngb.output(SocketType.Bundle, "Detail")

        result[SocketName.Enabled] << True
        normal >> result[SocketName.Normal]
        (color_m * 2 - 1) * (color_s * 2) >> result[SocketName.Color]
        def value(map: LinkBuilderBase, strength: LinkBuilderBase): return (1 - ((1 - map) * strength)) - 1
        value(m_m, m_s) >> result[SocketName.Metallic]
        value(r_m, r_s) >> result[SocketName.Roughness]
        value(o_m, o_s) >> result[SocketName.Alpha]
        value(a_m, a_s) >> result[SocketName.AmbientOcclusion]



class BeamBSDF15(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BSDF"
    bl_label = "BNGS 1.5"
    bl_icon = 'SHADERFX'
    bl_nclass = "SHADER"
    bl_width_default = 240
    ng_color_tag = GroupColorTag.SHADER
    ng_version_mayor = 2


    def single_update(self):
        messages = self.runtime.messages
        messages.clear()

        LS = BeamBSDF15.Sockets
        for socket in (LS.BASE_COLOR_MAP, LS.METALLIC_MAP, LS.ROUGHNESS_MAP, LS.OPACITY_MAP, LS.AO_MAP, LS.EMISSIVE_MAP, LS.CC_MAP):
            if not NodeLayoutValidator(self).assert_image_colorspace(socket, ColorSpace.NON_COLOR):
                messages.append(f"- {socket.value}:")
                messages.append(f"{ColorSpace.NON_COLOR.value} Expected")


    class Sockets(StrEnum):
        BASE_COLOR_MAP = "Base Color Map"
        BASE_COLOR = "Base Color"
        INSTANCE_COLOR = "Instance Color"
        VERTEX_COLOR = "Vertex Color"
        METALLIC_MAP = "Metallic Map"
        METALLIC_FACTOR = "Metallic Factor"
        NORMAL = "Normal"
        ROUGHNESS_MAP = "Roughness Map"
        ROUGHNESS_FACTOR = "Roughness Factor"
        OPACITY_MAP = "Opacity Map"
        OPACITY_FACTOR = "Opacity Factor"
        INSTANCE_OPACITY = "Instance Opacity"
        AO_MAP = "Ambient Occlusion Map"
        DETAIL = "Detail"

        PALETTE = "Palette"
        EMISSIVE_MAP = "Emissive Map"
        EMISSIVE_FACTOR = "Emissive Factor"
        EMISSIVE_INTENSITY = "Emissive Intensity (nits)"
        INSTANCE_EMISSIVE = "Instance Emissive"
        VERTEX_EMISSIVE = "Vertex Emissive"
        RETRO_REFLECTIVITY = "Retro Reflectivity"
        RETRO_REFLECTIVITY_COLOR = "Retro Reflectivity Color"
        CC_MAP = "Clear Coat Map"
        CC_FACTOR = "Clear Coat Factor"
        CC_ROUGHNESS = "Clear Coat Roughness"
        CC_NORMAL = "Clear Coat Normal"


    def create_node_group(self, ngb: NodeGroupBuilder):

        LS = BeamBSDF15.Sockets

        c_m = ngb.input(_COLOR_TEXTURE, LS.BASE_COLOR_MAP)
        c_f = ngb.input(_COLOR_VALUE, LS.BASE_COLOR)
        ic_enabled = ngb.input(_BOOL_VALUE, LS.INSTANCE_COLOR) 
        vc_enabled = ngb.input(_BOOL_VALUE, LS.VERTEX_COLOR) 
        normal = ngb.input(_NORMAL_MIX, LS.NORMAL)
        m_m = ngb.input(_FLOAT_TEXTURE, LS.METALLIC_MAP)
        m_f = ngb.input(_FLOAT_VALUE, LS.METALLIC_FACTOR, 0)
        r_m = ngb.input(_FLOAT_TEXTURE, LS.ROUGHNESS_MAP)
        r_f = ngb.input(_FLOAT_VALUE, LS.ROUGHNESS_FACTOR)
        o_m = ngb.input(_FLOAT_TEXTURE, LS.OPACITY_MAP)
        o_f = ngb.input(_FLOAT_VALUE, LS.OPACITY_FACTOR)
        io_enabled = ngb.input(_BOOL_VALUE, LS.INSTANCE_OPACITY) 
        ao_m = ngb.input(_FLOAT_TEXTURE, LS.AO_MAP)
        output = ngb.output(SocketType.Closure, SocketName.BNGShader)

        ngb.panel("Advanced")
        detail_bundle = ngb.input(SocketType.Bundle, LS.DETAIL)
        palette_bundle = ngb.input(_BUNDLE_NODE, LS.PALETTE)
        e_m = ngb.input(_COLOR_TEXTURE, LS.EMISSIVE_MAP)
        e_f = ngb.input(_COLOR_VALUE, LS.EMISSIVE_FACTOR, COLOR_BLACK)
        e_i = ngb.input(_FLOAT_VALUE, LS.EMISSIVE_INTENSITY, -1)
        ie_enabled = ngb.input(_BOOL_VALUE, LS.INSTANCE_EMISSIVE) 
        ve_enabled = ngb.input(_BOOL_VALUE, LS.VERTEX_EMISSIVE) 
        rr_f = ngb.input(_FLOAT_VALUE, LS.RETRO_REFLECTIVITY, 0)
        rr_c = ngb.input(_COLOR_VALUE, LS.RETRO_REFLECTIVITY_COLOR, COLOR_BLACK)
        cc_m = ngb.input(_FLOAT_TEXTURE, LS.CC_MAP)
        cc_f = ngb.input(_FLOAT_VALUE, LS.CC_FACTOR, 0)
        cc_r = ngb.input(_FLOAT_VALUE, LS.CC_ROUGHNESS)
        cc_n = ngb.input(_NORMAL_MIX, LS.CC_NORMAL)

        closure = ngb.nc.closure(BNGS_IO)
        closure.output >> output

        display_info = ngb.nc.seperate_bundle(DISPLAY_INFO, closure[SocketName.DisplayInfo])

        palette = ngb.nc.node(BeamPaletteEval, palette_bundle)
        palette_c = palette[SocketName.Color]
        palette_m = palette[SocketName.Metallic]
        palette_r = palette[SocketName.Roughness]
        palette_cc = palette[SocketName.ClearCoat]
        palette_cc_r = palette[SocketName.ClearCoatRoughness]

        detail = ngb.nc.seperate_bundle(DETAIL_LAYER, detail_bundle)
        detail_n = detail[SocketName.Normal]
        detail_c = detail[SocketName.Color] + 1
        detail_o = detail[SocketName.Alpha] + 1
        detail_m = detail[SocketName.Metallic] + 1
        detail_r = detail[SocketName.Roughness] + 1
        detail_ao = detail[SocketName.AmbientOcclusion] + 1

        object_info = ngb.nc.node(bpy.types.ShaderNodeObjectInfo)
        vc_info = ngb.nc.node(bpy.types.ShaderNodeVertexColor)

        ic = object_info[SocketName.Color]
        ia = object_info[SocketName.Alpha]
        vc = vc_info[SocketName.Color] 
        va = vc_info[SocketName.Alpha]

        normal = ngb.nc.node(BeamInvertBackfaceNormal, ngb.nc.node(BeamDetailNormal, normal, detail_n), closure[SocketName.InvertBackfaceNormals])

        # 1.5 color textures hold linear data, so the Non-Color images need no conversion
        c = c_m * c_f * detail_c * palette_c
        c = c.mix(c * ic, ic_enabled)
        c = c.mix(c * vc, vc_enabled)
        c = 0 | c & 1

        o = o_m * o_f * detail_o
        o = o.mix(o * ia, io_enabled)
        m = m_m * m_f * detail_m * palette_m
        r = r_m * r_f * detail_r * palette_r
        ao = ao_m * detail_ao

        e = e_m * e_f
        e = e.mix(e * e_i, e_i > -0.1)
        e = e.mix(e * ic, ie_enabled)
        e = e.mix(e * vc, ve_enabled)

        cc_w = cc_m * cc_f * palette_cc
        cc_r = cc_r * palette_cc_r

        retro = ngb.nc.node(BeamBSDFRetroReflect)
        c >> retro[SocketName.BaseColor]
        m >> retro[SocketName.Metallic]
        rr_f >> retro[SocketName.Factor]
        rr_c >> retro[SocketName.Color]
        normal >> retro[SocketName.Normal]

        principled = ngb.nc.node(bpy.types.ShaderNodeBsdfPrincipled)
        principled[SocketName.ThinWall] << True
        closure[SocketName.SubsurfaceScattering] >> principled[SocketName.SubsurfaceWeight]
        retro[SocketName.Normal] >> principled[SocketName.Normal]
        c >> principled[SocketName.BaseColor]
        m >> principled[SocketName.Metallic]
        r >> principled[SocketName.Roughness]
        cc_w >> principled[SocketName.CoatWeight]
        cc_r >> principled[SocketName.CoatRoughness]
        cc_n >> principled[SocketName.CoatNormal]

        emission_ao = ngb.nc.node(bpy.types.ShaderNodeEmission, COLOR_BLACK)
        emission_ao_strength = (1 - ao) * display_info[SocketName.AmbientOcclusionStrength]
        shader = principled.mix(emission_ao, emission_ao_strength)

        emission_e = ngb.nc.node(bpy.types.ShaderNodeEmission, e)
        shader += emission_e

        shader >> closure[SocketName.Shader]
        o >> closure[SocketName.Alpha]
        


class BeamStageMix(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}StageMix"
    bl_label = "BNGS 1.5 Mix"
    bl_nclass = "SHADER"
    ng_color_tag = GroupColorTag.SHADER


    class Sockets(StrEnum):
        BASE = "BNGS Base"
        OVERLAY = "BNGS Overlay"


    def create_node_group(self, ngb: NodeGroupBuilder):

        in_base = ngb.input(SocketType.Closure, BeamStageMix.Sockets.BASE)
        in_overlay = ngb.input(SocketType.Closure, BeamStageMix.Sockets.OVERLAY)
        output = ngb.output(SocketType.Closure, SocketName.BNGShader)

        base = ngb.nc.eval_closure(BNGS_IO, in_base)
        overlay = ngb.nc.eval_closure(BNGS_IO, in_overlay)
        base_alpha = base[SocketName.Alpha]
        overlay_alpha = overlay[SocketName.Alpha]

        closure = ngb.nc.closure(BNGS_IO)
        BNGS_IO.inputs.forward(closure, base)
        BNGS_IO.inputs.forward(closure, overlay)

        shader = ngb.nc.mix(overlay_alpha, base[SocketName.Shader], overlay[SocketName.Shader])
        alpha = base_alpha * (1.0 - overlay_alpha) + overlay_alpha
        shader >> closure[SocketName.Shader]
        alpha >> closure[SocketName.Alpha]

        closure.output >> output



class ReflectionMode(StrEnum):
    NONE = "None"
    LEVEL = "Level"
    CUBEMAP = "Cubemap"

_ENUM_INT_DICT: dict[ReflectionMode, int] = {
    ReflectionMode.NONE: 0,
    ReflectionMode.LEVEL: 1,
    ReflectionMode.CUBEMAP: 2,
}


def _BeamMaterial_update_reflection_mode(self: 'BeamMaterial', ctx: bpy.types.Context):
    butils.set_default_value(self.inputs[SocketName.ReflectionMode], _ENUM_INT_DICT.get(self.reflection_mode, 0))


def _BeamMaterial_update_blend_mode(self: 'BeamMaterial', ctx: bpy.types.Context):
    butils.set_default_value(self.inputs[SocketName.AlphaBlendMode], int(self.blend_mode != AlphaBlendMode.NONE))

    
class BeamMaterial(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}Material"
    bl_label = "BNG Material"
    bl_icon = "MATERIAL"
    bl_nclass = "SHADER"
    bl_width_default = 200
    ng_color_tag = GroupColorTag.SHADER


    reflection_mode: ReflectionMode
    reflection_cubemap: str

    blend_mode: AlphaBlendMode
    blend_z: bool
    blend_rshadows: bool


    class Sockets(StrEnum):
        BLEND_MODE = "Alpha Blend Mode"
        Z_WRITE = "Z-Write"
        RECEIVE_SHADOWS = "Receive Shadows"
        CLIP = "Alpha Clip"
        CLIP_T = "Alpha Clip Threshold"
        DOUBLE_SIDED = "Double Sided"
        INVERT_BACKFACE_NORMALS = SocketName.InvertBackfaceNormals
        SHADOWS = "Cast Shadows"
        SUBSURFACE_SCATTERING = SocketName.SubsurfaceScattering



    def draw_buttons(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        super().draw_buttons(context, layout)
        layout.use_property_decorate = False

        layout.use_property_split = True
        layout.prop(self, "blend_mode")
        if self.blend_mode != AlphaBlendMode.NONE:
            layout.use_property_split = False
            layout.prop(self, "blend_z")
            layout.prop(self, "blend_rshadows")

        layout.use_property_split = True
        layout.prop(self, "reflection_mode")
        if self.reflection_mode == ReflectionMode.CUBEMAP:
            layout.prop(self, "reflection_cubemap")


    def create_node_group(self, ngb: NodeGroupBuilder):
        
        LS = BeamMaterial.Sockets

        in_bngs = ngb.input(SocketType.Closure, SocketName.BNGShader)
        clip_enabled = ngb.input(_BOOL_VALUE, LS.CLIP)
        clip_t = ngb.input(_FLOAT_VALUE, LS.CLIP_T, default_value=0.5)
        ds_enabled = ngb.input(_BOOL_VALUE, LS.DOUBLE_SIDED)
        ibn_enabled = ngb.input(_BOOL_VALUE, LS.INVERT_BACKFACE_NORMALS, default_value=True)
        shadows_enabled = ngb.input(_BOOL_VALUE, LS.SHADOWS, default_value=True)
        subsurface = ngb.input(_FLOAT_VALUE, LS.SUBSURFACE_SCATTERING, default_value=0.0)
        output = ngb.output(SocketType.Shader, SocketName.Shader)

        ngb.panel("PRIVATE")
        r_mode = ngb.input(_INT_PRIVATE, SocketName.ReflectionMode, default_value=0)
        blend_mode = ngb.input(_INT_PRIVATE, SocketName.AlphaBlendMode, default_value=0)

        blend_enabled = blend_mode > 0.5

        eval = ngb.nc.eval_closure(BNGS_IO, in_bngs)
        ibn_enabled >> eval[SocketName.InvertBackfaceNormals]
        subsurface >> eval[SocketName.SubsurfaceScattering]
        r_mode >> eval[SocketName.ReflectionMode]
        blend_mode >> eval[SocketName.AlphaBlendMode]

        shader = eval[SocketName.Shader]
        alpha = eval[SocketName.Alpha]

        is_backfacing = ngb.nc.node(bpy.types.ShaderNodeNewGeometry)[SocketName.Backfacing]
        backface_discard = is_backfacing & ds_enabled.is_false()

        is_shadow_ray = ngb.nc.node(bpy.types.ShaderNodeLightPath)[SocketName.IsShadowRay]
        shadows_discard = is_shadow_ray & shadows_enabled.is_false()

        discard = (backface_discard | shadows_discard) | ((alpha < clip_t) & clip_enabled)
        blend_factor = (1 - alpha) & blend_enabled

        transparent = ngb.nc.node(bpy.types.ShaderNodeBsdfTransparent)
        shader.mix(transparent, blend_factor | discard) >> output

BeamMaterial.annotate(
    reflection_mode= bpy.props.EnumProperty(
        name=SocketName.ReflectionMode,
        items=[
            (ReflectionMode.NONE, ReflectionMode.NONE, ""),
            (ReflectionMode.LEVEL, ReflectionMode.LEVEL, ""),
            (ReflectionMode.CUBEMAP, ReflectionMode.CUBEMAP, ""),
        ],
        default=ReflectionMode.NONE,
        update=_BeamMaterial_update_reflection_mode
    ),
    reflection_cubemap= bpy.props.StringProperty(name="Cubemap", default="none"),
    blend_mode= bpy.props.EnumProperty(
        name=SocketName.AlphaBlendMode,
        items=[
            (AlphaBlendMode.NONE, AlphaBlendMode.NONE, ""),
            (AlphaBlendMode.PRE_MUL_ALPHA, AlphaBlendMode.PRE_MUL_ALPHA, ""),
            (AlphaBlendMode.ADD, AlphaBlendMode.ADD, ""),
            (AlphaBlendMode.ADD_ALPHA, AlphaBlendMode.ADD_ALPHA, ""),
            (AlphaBlendMode.LERP_ALPHA, AlphaBlendMode.LERP_ALPHA, ""),
            (AlphaBlendMode.MUL, AlphaBlendMode.MUL, ""),
            (AlphaBlendMode.SUB, AlphaBlendMode.SUB, ""),
        ],
        default=AlphaBlendMode.NONE,
        update=_BeamMaterial_update_blend_mode
    ),
    blend_z= bpy.props.BoolProperty(name="Z-Write"),
    blend_rshadows= bpy.props.BoolProperty(name="Receive Shadows")
)


class ShaderNodeTree(Menu):

    bl_idname = "GRILLEBEAMNG_MT_ShaderNodeTree"
    bl_label = "BeamNG"
    tree_type = NodeName.ShaderNodeTree
    node_items: list[object] = [
        "Material",
        BeamBSDF15,
        BeamBSDF15Detail,
        BeamStageMix,
        BeamBDSF10Basic,
        BeamBSDFCollision,
        BeamMaterial, 
        None,
        "Input",
        BeamRGBA,
        BeamUVAnimation,
        BeamUVData,
        BeamImageTex,
        BeamImageTexConverter,
        BeamPalette,
        BeamPaint,
        BeamDisplayInject,
    ]


    @classmethod
    def poll(cls, context) -> bool:
        return context.space_data.tree_type == cls.tree_type # type: ignore


    def draw(self, context):

        layout = self.layout
        for item in self.node_items:

            if item is None:
                layout.separator()
                continue

            elif isinstance(item, str):
                layout.label(text=item, icon="REMOVE")

            elif isinstance(item, type) and issubclass(item, BaseShaderNode):
                op = layout.operator("node.add_node", text=item.bl_label)
                op.type = item.bl_idname
                op.use_transform = True

            else: raise Exception()


    @staticmethod
    def addmenu_append(menu: Menu, context: bpy.types.Context):
        tree_type = context.space_data.tree_type # type: ignore
        if tree_type != ShaderNodeTree.tree_type:
            return
        menu.layout.menu(ShaderNodeTree.bl_idname)



def _iter_shader_trees():
    for id in (*bpy.data.materials, *bpy.data.worlds, *bpy.data.lights):
        if id.node_tree is not None: yield id.node_tree
    for group in bpy.data.node_groups:
        if isinstance(group, bpy.types.ShaderNodeTree): yield group


def _find_minor_outdated():
    nodes = [node for tree in _iter_shader_trees() for node in tree.nodes if isinstance(node, BaseShaderNode) and node.is_node_group_minor_outdated]
    # innermost first, rebuilding an outer group would otherwise step nested groups aside that only the old outer group uses
    for node in nodes:
        stale = not_none(node.node_tree)
        if not any(other.id_data == stale for other in nodes):
            return stale, [other for other in nodes if other.node_tree == stale]
    return None


def update_node_groups():
    """
    Minor updates keep the interface, so outdated groups are swapped for fresh ones, links and values survive.
    One group at a time, removing a group also removes the nodes nested in it.
    """
    while (found := _find_minor_outdated()) is not None:
        stale, nodes = found
        fresh = nodes[0].get_node_group()
        for node in nodes:
            node.node_tree = fresh
            node.apply_socket_data()
        bpy.data.node_groups.remove(stale)


_DEFERRED_UPDATES: dict[int, bpy.types.NodeTree] = {}


def apply_deferred_updates() -> None:
    """Runs the updates nodes deferred with defer_update. A timer calls it, background scripts (tests) call it directly."""
    import traceback
    pending = list(_DEFERRED_UPDATES.items())
    _DEFERRED_UPDATES.clear()
    for pointer, tree in pending:
        # the tree or node may be gone by now (deleted, undo, file loaded)
        try: node: bpy.types.Node | None = next((node for node in tree.nodes if node.as_pointer() == pointer), None)
        except ReferenceError: continue
        if not isinstance(node, BaseShaderNode): continue
        runtime = node.runtime
        runtime.updating = True
        try: node.deferred_update()
        except Exception: traceback.print_exc()
        finally: runtime.updating = False
    return None


@bpy.app.handlers.persistent
def _load_post(*args: object):
    update_node_groups()



class OT_UpdateNodeGroup(basetypes.Operator):
    bl_idname = "grille.update_beamng_node"
    bl_label = "Update BNG Node"
    bl_description = "Update the node to the current version, links and values follow by socket name"
    bl_options = {'REGISTER', 'UNDO'}


    @classmethod
    def poll(cls, context):
        node = getattr(context, "node", None)
        return isinstance(node, BaseShaderNode) and node.is_node_group_mayor_outdated


    def execute(self, context):
        node = cast(BaseShaderNode, getattr(context, "node"))
        lost = node.update_node_group_mayor()
        for msg in lost: print(f"{node.name}: {msg}")
        if lost: self.report({'WARNING'}, f"{node.name}: {', '.join(lost)}")
        return {'FINISHED'}



class ShaderNodeRegistry:

    nodes: list[type[BaseShaderNode]] = [
        BeamBSDF15, 
        BeamBDSF10Basic,
        BeamBSDFCollision,
        BeamStageMix, 
        BeamMaterial, 
        BeamFactorColor, 
        BeamFactorFloat,
        BeamUVAnimation,
        BeamDetailNormal,
        BeamInvertBackfaceNormal,
        BeamImageTex,
        BeamImageTexConverter,
        BeamRGBA,
        BeamRGBAMix,
        BeamRGBADefault,
        BeamRGBAMath,
        BeamNormalOrDefault,
        BeamONHardLight,
        BeamPaint,
        BeamPalette,
        BeamPaletteEval,
        BeamBSDF15Detail,
        BeamBSDFRetroReflect,
        BeamUVData,
        BeamDisplayInject,
    ]


    @staticmethod
    def register():
        for cls in ShaderNodeRegistry.nodes:
            bpy.utils.register_class(cls)

        bpy.utils.register_class(ShaderNodeTree)
        bpy.types.NODE_MT_add.append(ShaderNodeTree.addmenu_append) # type: ignore
        bpy.utils.register_class(OT_UpdateNodeGroup)
        bpy.app.handlers.load_post.append(_load_post)


    @staticmethod
    def unregister():
        if bpy.app.timers.is_registered(apply_deferred_updates): bpy.app.timers.unregister(apply_deferred_updates)
        _DEFERRED_UPDATES.clear()
        bpy.app.handlers.load_post.remove(_load_post)
        bpy.utils.unregister_class(OT_UpdateNodeGroup)
        bpy.types.NODE_MT_add.remove(ShaderNodeTree.addmenu_append) # type: ignore
        bpy.utils.unregister_class(ShaderNodeTree)

        for cls in ShaderNodeRegistry.nodes:
            bpy.utils.unregister_class(cls)