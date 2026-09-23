
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

NODE_SOCKET_SHAPE = SocketShape.CIRCLE
TEXTURE_SOCKET_SHAPE = SocketShape.DIAMOND
VALUE_SOCKET_SHAPE = SocketShape.LINE
TVMIX_SOCKET_SHAPE = SocketShape.SQUARE
DISPLAY_SOCKET_SHAPE = SocketShape.CIRCLE_DOT

COLOR_WHITE = Color4F.WHITE
COLOR_BLACK = Color4F.BLACK
COLOR_GRAY = (0.5,0.5,0.5,1)
COLOR_NULL = (0,0,0,0)
COLOR_NULL_HALF = (0.5,0.5,0.5,0.5)
COLOR_RED = (1,0,0,1)

_BOOL_VALUE = _SCI(SocketType.Bool, VALUE_SOCKET_SHAPE, False)
_MENU = _SCI(SocketType.Menu, VALUE_SOCKET_SHAPE, False)
_FLOAT = _SCI.FACTOR
_FLOAT_VALUE = _SCI(SocketType.Float, VALUE_SOCKET_SHAPE, False, default_value=1, **_SCI.FACTOR.kwargs)
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
        return self.nc.node(BeamRGBADefault, value, color=default_value)

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



_NODE_GROUP_DATA_RUNTIME_DICT: dict[int, NodeGroupData] = {}


def _BaseShaderNode_init(self: 'BaseShaderNode', ctx: bpy.types.Context):
    return self.init(ctx)


def _BaseShaderNode_post_init(self: 'BaseShaderNode', ctx: bpy.types.Context):
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


    @classmethod
    def poll(cls, node_tree):
        if node_tree is None: return False
        return node_tree.bl_idname == NodeName.ShaderNodeTree
    

    def get_validator(self):
        return NodeLayoutValidator(self, None, self.runtime.messages)


    def init(self, context):
        tree = self.get_node_group()
        self.node_tree = tree

        if NODE_GROUP_JSON_KEY in tree:
            ptr = tree.as_pointer()
            ngdata = _NODE_GROUP_DATA_RUNTIME_DICT.get(ptr, None)
            if ngdata is None:
                ngdata =  NodeGroupData.from_text(tree[NODE_GROUP_JSON_KEY])
                _NODE_GROUP_DATA_RUNTIME_DICT[ptr] = ngdata

            for key in ngdata.inputs: ngdata.inputs[key].apply(self.inputs[key])
            for key in ngdata.outputs: ngdata.outputs[key].apply(self.outputs[key])

        self.post_init()


    def post_init(self):
        pass


    def draw_buttons(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        messages = self.runtime.messages
        if len(messages) > 0:
            col = layout.column()
            col.scale_y = 0.8
            col.alert = True
            for msg in messages:
                col.label(text=msg)


    def get_node_group_name(self):
        return f".{self.bl_idname}_v{self.ng_version_mayor}"

    
    def get_node_group(self): 
        group_name = self.get_node_group_name()

        if self.ng_shared and group_name in bpy.data.node_groups:
            group = bpy.data.node_groups[group_name]
            if isinstance(group, bpy.types.ShaderNodeTree): return group
            else: raise Exception()
        
        ngb = _Extended_NGB(group_name)
        self.create_node_group(ngb)
        ngb.arrange_nodes()
        tree = ngb.tree
        tree.color_tag = self.ng_color_tag # pyright: ignore[reportAttributeAccessIssue]
        _NODE_GROUP_DATA_RUNTIME_DICT[tree.as_pointer()] = ngb.ngdata
        tree[NODE_GROUP_JSON_KEY] = ngb.ngdata.dump()
        tree[NODE_GROUP_VERSION_MAYOR_KEY] = self.ng_version_mayor
        tree[NODE_GROUP_VERSION_MINOR_KEY] = self.ng_version_minor

        return tree


    def create_node_group(self, ngb: _Extended_NGB):
        pass



class BeamImageTex(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}TexImg"
    bl_label = "BNG Image Texture"
    #bl_icon = 'TEXTURE'

    bl_width_default = 240
    ng_color_tag = GroupColorTag.TEXTURE

    _updating = False


    class ImageType(StrEnum):
        COLOR_RGBA = "Color RGBA"
        COLOR_RGB = "Color RGB"
        NORMAL = "Normal"
        DATA = "Data"


    # Custom properties
    image: bpy.types.Image | None
    image_type: ImageType


    def get_node_group_name(self):
        base_name = super().get_node_group_name()
        return base_name if self.image is None else f"{base_name}_{self.image.name_full}"
    

    def create_node_group(self, ngb):

        LS = BeamImageTex.ImageType

        in_strength = ngb.input(_FLOAT_VALUE, SocketName.Strength)
        in_uv = ngb.input(_UV_NODE, SocketName.Vector)
        out_color = ngb.output(_COLOR_TEXTURE, LS.COLOR_RGB)
        out_rgba = ngb.output(_RGBA_TEXTURE, LS.COLOR_RGBA)
        out_normal = ngb.output(_NORMAL_MIX, LS.NORMAL)
        out_data = ngb.output(_FLOAT_TEXTURE, LS.DATA)

        imgtex = ngb.nc.node(bpy.types.ShaderNodeTexImage, image = self.image)
        normal_map = ngb.nc.node(bpy.types.ShaderNodeNormalMap)

        in_uv >> imgtex[SocketName.Vector]

        imgtex[SocketName.Color] >> out_color

        in_strength >> normal_map[SocketName.Strength]
        imgtex[SocketName.Color] >> normal_map[SocketName.Color]
        normal_map[SocketName.Normal] >> out_normal


    def draw_buttons(self, context, layout):
        super().draw_buttons(context, layout)
        layout.template_ID(self, "image_ptr", open="image.open", new="image.new")
        #layout.prop(self, "image_type", text="Type")
        #self.check_image_type(layout)
        #layout.prop(self, "uv_map")
        #uv1hint = getattr(context.space_data.id, MaterialProperties.UV1_HINT)
        #layout.label(text=f"UV Map Index: {1 if uv1hint in self.uv_map else 0}")

BeamImageTex.anotate(
    image = props.Pointer(name="Image", type=bpy.types.Image, update=_BaseShaderNode_init),
    image_type = BeamImageTex.ImageType.to_bpy_enum("Type", default=BeamImageTex.ImageType.COLOR_RGBA, update=_BaseShaderNode_init)
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



class BeamDetailUVScale(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}DetailUVSCale"
    bl_label = "BNG Detail UV Scale"
    bl_nclass = "OP_VECTOR"
    ng_color_tag = GroupColorTag.VECTOR


    def create_node_group(self, ngb: NodeGroupBuilder):
        pass
        
        # ngb.create_vector_input("UV", True)
        # ngb.create_vector_input("Scale", default_value=(1.0,1.0,1.0), subtype="XYZ", dimensions=2)
        # #ngb.create_float_input("Scale V", default_value=1.0, range=None, subtype=None)
        # ngb.create_vector_output("UV")

        # inputs, outputs = ngb._create_io()

        # #vec = ngb.create_node(NodeName.CombineXYZ)
        # mul = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)

        # #ngb.link(inputs, 1, vec, 0)
        # #ngb.link(inputs, 2, vec, 1)

        # ngb.link(inputs, 0, mul, 0)
        # ngb.link(inputs, 1, mul, 1)
        # ngb.link(mul, 0, outputs)



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

    bl_idname = f"{SHADER_NODE_PREFIX}UVAnimation"
    bl_label = "BNG UV Animation"
    ng_color_tag = GroupColorTag.VECTOR


    class Sockets(StrEnum):
        UV = "UV"
        ANIMATION = "Animation"
        ROTATION_PIVOT_OFFSET = "Rotation Pivot Offset"
        ROTATION_SPEED = "Rotation Speed"
        SCROLL_FACTOR = "Scroll Factor"
        SCROLL_SPEED = "Scroll Speed"
        WAVE_TYPE = "Wave Type"
        WAVE_SCALE = "Wave Scale"
        WAVE_AMPLITUDE = "Wave Amplitude"
        WAVE_FREQUENCY = "Wave Frequency"
        FRAMES_SEC = "Frames/Sec"
        FRAMES = "Frames"
        TIME_SOURCE = "Time"
        SECONDS = "Seconds"


    class WaveType(StrEnum):
        NONE = "None"
        SIN = "Sin"
        SQUARE = "Square"
        TRIANGLE = "Triangle"


    class TimeSource(StrEnum):
        SCENE = "Scene Time"
        VALUE = "Value"


    def create_node_group(self, ngb: NodeGroupBuilder):

        LS = BeamUVAnimation.Sockets

        time_source_input = ngb.input(_MENU, LS.TIME_SOURCE)
        time_source_value = ngb.input(_FLOAT, LS.SECONDS)
        
        ngb.output(_BUNDLE_NODE, LS.ANIMATION)

        ngb.panel("Rotation")
        ngb.input(_VEC2_VALUE, LS.ROTATION_PIVOT_OFFSET)
        rot_speed = ngb.input(_FLOAT_VALUE, LS.ROTATION_SPEED, 0)

        ngb.panel("Scroll")
        ngb.input(_VEC2_VALUE, LS.SCROLL_FACTOR)
        ngb.input(_FLOAT_VALUE, LS.SCROLL_SPEED, 0)

        ngb.panel("Wave")
        menu_socket = ngb.input(_MENU, LS.WAVE_TYPE)
        ngb.input(_BOOL_VALUE, LS.WAVE_SCALE)
        ngb.input(_FLOAT_VALUE, LS.WAVE_AMPLITUDE, 0)
        ngb.input(_FLOAT_VALUE, LS.WAVE_FREQUENCY, 0)

        ngb.panel("Image Sequence")
        ngb.input(_FLOAT_VALUE, LS.FRAMES_SEC, 0)
        ngb.input(_FLOAT_VALUE, LS.FRAMES, 0)

        seconds = ngb.nc.menu_switch(SocketType.Float, *BeamUVAnimation.TimeSource, menu=time_source_input)
        ngb.nc.node(bpy.types.GeometryNodeInputSceneTime)[LS.SECONDS] >> seconds[BeamUVAnimation.TimeSource.SCENE]
        time_source_value >> seconds[BeamUVAnimation.TimeSource.VALUE]


        ngb.nc.menu_switch(SocketType.Float, *BeamUVAnimation.WaveType, menu=menu_socket)

        #sin = ngb.nc.math("SINE", seconds)



class BeamDetailColor(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}DetailColor"
    bl_label = "BNG Detail Color"
    bl_nclass = "OP_COLOR"
    ng_color_tag = GroupColorTag.COLOR


    def update(self):
        messages = self.runtime.messages
        messages.clear()
        nlv = NodeLayoutValidator(self)

        if nlv.try_follow(1):
            if nlv.is_node_idname(BeamFactorColor.bl_idname):
                messages.append("- Base:")
                messages.append(f"{BeamFactorColor.bl_label} must come after {BeamDetailColor.bl_label}")


    # def post_init(self):
    #     self.inputs["Strength"].display_shape = VALUE_SOCKET_SHAPE
    #     self.inputs["Base"].display_shape = TEXTURE_SOCKET_SHAPE
    #     self.inputs["Detail"].display_shape = TEXTURE_SOCKET_SHAPE
    #     self.outputs["Result"].display_shape = TEXTURE_SOCKET_SHAPE


    # def create_node_group(self, ngb: NodeGroupBuilder):

    #     ngb.create_float_input("Strength")
    #     ngb.create_color_input("Base", True, default_value=(1.0,1.0,1.0,1.0))
    #     ngb.create_color_input("Detail", True, default_value=(0.5,0.5,0.5,1.0))

    #     ngb.create_color_output("Result")

    #     inputs, outputs = ngb._create_io()

    #     separate = ngb.create_node(NodeName.SeparateColor, mode='HSV')
    #     greater = ngb.create_math(Operation.GREATER_THAN, value1=0.5)

    #     light_multiply = ngb.create_math(Operation.MULTIPLY, value1=1.0)
    #     light_vm_sub  = ngb.create_node(NodeName.VectorMath, operation=Operation.SUBTRACT)
    #     light_vm_sub.inputs[1].default_value = (0.5,0.5,0.5)
    #     light_vm_mul  = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)
    #     light_vm_add  = ngb.create_node(NodeName.VectorMath, operation=Operation.ADD)

    #     def create_mix(mode: str):
    #         mix = ngb.create_node(
    #             NodeName.Mix,
    #             data_type = Operation.RGBA,
    #             blend_type = mode,
    #             clamp_factor = False,
    #             clamp_result = False,
    #         )
    #         bpy.context.view_layer.update()
    #         return mix
        
    #     mix = create_mix(Operation.MIX)
    #     dark = create_mix(Operation.LINEAR_LIGHT)

    #     ngb.link(light_vm_sub, 0, light_vm_mul, 0)
    #     ngb.link(light_vm_mul, 0, light_vm_add, 0)

    #     ngb.link(inputs, 0, dark, 0)
    #     ngb.link(inputs, 0, light_multiply, 0)
    #     ngb.link(light_multiply, 0, light_vm_mul, 1)

    #     ngb.link(inputs, 1, dark, SocketIndex.MixColorIn0)
    #     ngb.link(inputs, 1, light_vm_add, 1)

    #     ngb.link(inputs, 2, dark, SocketIndex.MixColorIn1)
    #     ngb.link(inputs, 2, light_vm_sub, 0)
    #     ngb.link(inputs, 2, separate, 0)

    #     ngb.link(separate, 2, greater, 0)
    #     ngb.link(greater, 0, mix, 0)
    #     ngb.link(dark, SocketIndex.MixColorOut, mix, SocketIndex.MixColorIn0)
    #     ngb.link(light_vm_add, 0, mix, SocketIndex.MixColorIn1)

    #     ngb.link(mix, SocketIndex.MixColorOut, outputs, 0)



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
    bl_label = "BNG Collision BSDF"
    bl_icon = 'MOD_PHYSICS'
    bl_nclass = "SHADER"
    bl_width_default = 200
    ng_color_tag = GroupColorTag.SHADER


    def create_node_group(self, ngb: NodeGroupBuilder):
        pass



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
        layout.prop(self, "color", text="")

BaseBeamRGBA.anotate(
    color_value = bpy.props.FloatVectorProperty(
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



class BeamMathHardLight(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}MathHardLight"
    bl_label = "BNG HardLight"
    ng_color_tag = GroupColorTag.CONVERTER

    def create_node_group(self, ngb: NodeGroupBuilder):

        i = ngb.input(_FLOAT_VALUE, "I")
        m = ngb.input(_FLOAT_VALUE, "M")

        dark = 2 * i * m
        light = 1 - (2 * (1 - m) * (1 - i))

        dark.mix(light, m > 0.5) >> ngb.output(_FLOAT_VALUE, SocketName.Value)



class BeamRGBAMath(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Math"
    bl_label = "BNG RGBA Math"
    ng_color_tag = GroupColorTag.COLOR


    operation: Operation

    def get_node_group_name(self):
        return f"{super().get_node_group_name()}_{self.operation}"


    def create_node_group(self, ngb):

        b_default_value = (1,1,1,1) if self.operation == Operation.MULTIPLY or self.operation == Operation.DIVIDE else (0,0,0,0)
        a = ngb.RGBA_input("A")
        b = ngb.RGBA_input("B", b_default_value)

        if self.operation == Operation.OVERLAY:
            ngb.RGBA_output("Result", ngb.nc.mix(b[1], a[0], b[0]), a[1])
        elif self.operation == Operation.HARD_LIGHT:
            a_rgb = ngb.nc.node(bpy.types.ShaderNodeSeparateColor, a)
            b_rgb = ngb.nc.node(bpy.types.ShaderNodeSeparateColor, b)
            red = ngb.nc.node(BeamMathHardLight, a_rgb[0], b_rgb[0])
            green = ngb.nc.node(BeamMathHardLight, a_rgb[1], b_rgb[1])
            blue = ngb.nc.node(BeamMathHardLight, a_rgb[2], b_rgb[2])
            color = ngb.nc.node(bpy.types.ShaderNodeCombineColor, red, green, blue)
            alpha = ngb.nc.node(BeamMathHardLight, a[1], b[1])
            ngb.RGBA_output("Result", color, alpha)
        else:
            color = ngb.nc.math(self.operation, a[0], b[0]) 
            alpha = ngb.nc.math(self.operation, a[1], b[1]) 
            ngb.RGBA_output("Result", color, alpha)


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

    def create_node_group(self, ngb):

        pmap = ngb.input(_COLOR_TEXTURE, "Palette Map", COLOR_RED)
        color_enabled = ngb.input(_BOOL_VALUE, SocketName.Color, True)
        metallic_enabled = ngb.input(_BOOL_VALUE, SocketName.Metallic, True)
        roughness_enabled = ngb.input(_BOOL_VALUE, SocketName.Roughness, True)
        cc_enabled = ngb.input(_BOOL_VALUE, SocketName.ClearCoat, True)
        ccr_enabled = ngb.input(_BOOL_VALUE, SocketName.ClearCoatRoughness, True)
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

        result >> ngb.output(_BUNDLE_NODE, "Palette")



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

        BNGS_INPUT.forward(closure, eval, exclude=(SocketName.DisplayInfo))
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

 
    def update(self):
        messages = self.runtime.messages
        messages.clear()
        nlv = NodeLayoutValidator(self)

        if not nlv.assert_image_colorspace(SocketName.BaseColor, ColorSpace.NON_COLOR):
            messages.append(f"- {SocketName.BaseColor.value}:")
            messages.append(f"{ColorSpace.NON_COLOR.value} Expected")


    class Sockets(StrEnum):
        BASE_COLOR_MAP = "Base Color Map"
        BASE_COLOR = "Base Color"
        INSTANCE_COLOR = "Instance Color"
        VERTEX_COLOR = "Vertex Color"
        METALLIC_MAP = "Metallic Map"
        METALLIC_FACTOR = "Mettalic Factor"
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
        m_f = ngb.input(_FLOAT_VALUE, LS.METALLIC_FACTOR)
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


    def create_node_group(self, ngb: NodeGroupBuilder):

        in_base = ngb.input(SocketType.Closure, "BNGS Base")
        in_overlay = ngb.input(SocketType.Closure, "BNGS Overlay")
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

BeamMaterial.anotate(
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
        "Material V1.5",
        BeamBSDF15,
        BeamBSDF15Detail,
        BeamStageMix, 
        BeamMaterial, 
        None,
        "Material V1",
        BeamMaterial, 
        BeamBDSF10Basic,
        BeamRGBA,
        BeamRGBAMix,
        BeamRGBADefault,
        BeamRGBAMath,
        None,
        "Factor", 
        BeamFactorColor, 
        BeamFactorFloat, 
        None,
        "Detail",
        BeamDetailUVScale, 
        BeamUVAnimation,
        BeamDetailColor, 
        BeamDetailNormal,
        None,
        "Utils",
        BeamBSDFCollision,
        BeamImageTex,
        BeamMathHardLight,
        BeamPalette,
        BeamPaint,
        BeamPaletteEval,
        BeamBSDFRetroReflect,
        BeamUVData,
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



class ShaderNodeRegistry:

    nodes: list[type[BaseShaderNode]] = [
        BeamBSDF15, 
        BeamBDSF10Basic,
        BeamBSDFCollision,
        BeamStageMix, 
        BeamMaterial, 
        BeamFactorColor, 
        BeamFactorFloat, 
        BeamDetailUVScale, 
        BeamUVAnimation,
        BeamDetailColor, 
        BeamDetailNormal,
        BeamInvertBackfaceNormal,
        BeamImageTex,
        BeamRGBA,
        BeamRGBAMix,
        BeamRGBADefault,
        BeamRGBAMath,
        BeamNormalOrDefault,
        BeamMathHardLight,
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


    @staticmethod
    def unregister():
        bpy.types.NODE_MT_add.remove(ShaderNodeTree.addmenu_append) # type: ignore
        bpy.utils.unregister_class(ShaderNodeTree)

        for cls in ShaderNodeRegistry.nodes:
            bpy.utils.unregister_class(cls)