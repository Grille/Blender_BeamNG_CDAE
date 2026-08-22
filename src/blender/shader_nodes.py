import bpy
from enum import Enum

from .material_properties import *
from .enums import *
from .shader_nodes_utils import *
from .shader_node_builder import NodeGroupBuilder, SocketCreateInfo, NodeGroupData
_Signature = NodeGroupBuilder.Signature
_SCI = SocketCreateInfo
#_NS = NodeGroupBuilder.NodeSocket

# pyright: reportInvalidTypeForm=false

NODE_GROUP_JSON_KEY = "grille_beamng_cdae_ngjson"
NODE_GROUP_VERSION_MAYOR_KEY = "grille_beamng_cdae_mayor_version"
NODE_GROUP_VERSION_MINOR_KEY = "grille_beamng_cdae_minor_version"
SHADER_NODE_PREFIX = "ShaderNodeCustom.grille_beamng_cdae_"

RGBA =_Signature(
    _Signature.Socket(SocketName.Color, SocketType.Color),
    _Signature.Socket(SocketName.Alpha, SocketType.Float),
    _Signature.Socket(SocketName.Enabled, SocketType.Bool),
)

BNGS_INPUT = _Signature(
    _Signature.Socket(SocketName.InvertBackfaceNormals, SocketType.Bool),
    _Signature.Socket(SocketName.ReflectionMode, SocketType.Integer),
    _Signature.Socket(SocketName.SubsurfaceScattering, SocketType.Float)
)
BNGS_OUTPUT = _Signature(
    _Signature.Socket(SocketName.Shader, SocketType.Shader),
    _Signature.Socket(SocketName.Alpha, SocketType.Float)
)
BNGS_IO = _Signature.IO(BNGS_INPUT, BNGS_OUTPUT)

TEXTURE_SOCKET_SHAPE = SocketShape.DIAMOND
VALUE_SOCKET_SHAPE = SocketShape.LINE
PRIVATE_SOCKET_SHAPE = SocketShape.LIST

COLOR_WHITE = (1,1,1,1)
COLOR_BLACK = (0,0,0,1)
COLOR_NULL = (0,0,0,0)
COLOR_NULL_HALF = (0.5,0.5,0.5,0.5)

_BOOL_VALUE = _SCI(SocketType.Bool, VALUE_SOCKET_SHAPE, False)
_FLOAT = _SCI.FACTOR
_FLOAT_VALUE = _SCI(SocketType.Float, VALUE_SOCKET_SHAPE, False, default_value=1, **_SCI.FACTOR.kwargs)
_FLOAT_TEXTURE = _SCI(SocketType.Float, TEXTURE_SOCKET_SHAPE, True, default_value=1)
_COLOR = _SCI.COLOR
_COLOR_VALUE = _SCI(SocketType.Color, VALUE_SOCKET_SHAPE, False, default_value=COLOR_WHITE)
_COLOR_TEXTURE = _SCI(SocketType.Color, TEXTURE_SOCKET_SHAPE, True, default_value=COLOR_WHITE)
_RGBA_X = _SCI(SocketType.Bundle)
_RGBA_VALUE = _SCI(SocketType.Bundle, VALUE_SOCKET_SHAPE, False)
_RGBA_TEXTURE = _SCI(SocketType.Bundle, TEXTURE_SOCKET_SHAPE, True)
_NORMAL = _SCI(SocketType.Vector, SocketShape.CIRCLE, True)
_INT_PRIVATE = _SCI(SocketType.Integer, PRIVATE_SOCKET_SHAPE, False)
_VEC2 = _SCI.VEC2
_VEC3 = _SCI.VEC3



class NodeRuntimeData:

    _node_runtime_dict: dict[int, "NodeRuntimeData"] = {}


    @staticmethod
    def get_instance(node: bpy.types.Struct):
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

class BaseShaderNode(bpy.types.ShaderNodeCustomGroup):

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
    def poll(cls, ntree: bpy.types.NodeTree):
        return ntree.bl_idname == NodeName.ShaderNodeTree
    

    def get_validator(self):
        return NodeLayoutValidator(self, None, self.runtime.messages)


    def init(self, context):
        tree = self.node_tree = self.get_node_group()

        if NODE_GROUP_JSON_KEY in tree:
            ptr = tree.as_pointer()
            ngdata = _NODE_GROUP_DATA_RUNTIME_DICT.get(ptr, None)
            if ngdata is None:
                ngdata =  NodeGroupData.from_text(tree[NODE_GROUP_JSON_KEY])
                _NODE_GROUP_DATA_RUNTIME_DICT[ptr] = ngdata
            for key in ngdata.input_shapes: self.inputs[key].display_shape = ngdata.input_shapes[key]
            for key in ngdata.output_shapes: self.outputs[key].display_shape = ngdata.output_shapes[key]

        self.post_init()


    def post_init(self):
        pass


    def draw_buttons(self, context, layout):
        messages = self.runtime.messages
        if len(messages) > 0:
            col = layout.column()
            col.scale_y = 0.8
            col.alert = True
            for msg in messages:
                col.label(text=msg)


    def get_node_group_name(self):
        return f"{self.bl_idname}_v{self.ng_version_mayor}"

    
    def get_node_group(self): 
        group_name = self.get_node_group_name()

        if self.ng_shared and group_name in bpy.data.node_groups:
            return bpy.data.node_groups[group_name]
        
        ngb = NodeGroupBuilder(group_name)
        self.create_node_group(ngb)
        ngb.arrange_nodes()
        tree = ngb.tree
        tree.color_tag = self.ng_color_tag
        _NODE_GROUP_DATA_RUNTIME_DICT[tree.as_pointer()] = ngb.ngdata
        tree[NODE_GROUP_JSON_KEY] = ngb.ngdata.dump()
        tree[NODE_GROUP_VERSION_MAYOR_KEY] = self.ng_version_mayor
        tree[NODE_GROUP_VERSION_MINOR_KEY] = self.ng_version_minor

        return tree


    def create_node_group(self, ngb: NodeGroupBuilder):
        pass



class BeamImageTex(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}TexImg"
    bl_label = "BNG Image Texture"
    #bl_icon = 'TEXTURE'

    bl_width_default = 240
    ng_color_tag = GroupColorTag.TEXTURE

    _updating = False


    class ImageType(StrEnum):
        SRGB = "Color sRGBA"
        COLOR = "Color"
        NORMAL = "Normal"
        DATA = "Data"


    # Custom properties
    image_ptr: bpy.props.PointerProperty(type=bpy.types.Image, update=lambda self, ctx: self.update_image(ctx))
    image_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            (ImageType.COLOR, "Color", ""),
            (ImageType.SRGB, "Color HDR", ""),
            (ImageType.NORMAL, "Normal", ""),
            (ImageType.DATA, "Data", ""),
        ],
        default=ImageType.SRGB,
        update=lambda self, ctx: self.update_type(ctx)
    )


    @property
    def image(self) -> bpy.types.Image: return self.image_ptr



    def update_image(self, ctx):
        self.init(ctx)


    def update_type(self, ctx):
        pass


    def get_node_group_name(self):
        base_name = super().get_node_group_name()
        return base_name if self.image is None else f"{base_name}_{self.image.name_full}"
    

    def create_node_group(self, ngb):

        LS = BeamImageTex.ImageType

        in_strength = ngb.input(_FLOAT_VALUE, SocketName.Strength)
        in_uv = ngb.input(_NORMAL, SocketName.Vector)
        out_color = ngb.output(_COLOR_TEXTURE, LS.COLOR)
        out_rgba = ngb.output(_RGBA_TEXTURE, LS.SRGB)
        out_normal = ngb.output(_NORMAL, LS.NORMAL)
        out_data = ngb.output(_FLOAT_TEXTURE, LS.DATA)

        imgtex = ngb.nc.node(bpy.types.ShaderNodeTexImage, image = self.image)
        normal_map = ngb.nc.node(bpy.types.ShaderNodeNormalMap)

        in_uv >> imgtex[SocketName.Vector]

        imgtex[SocketName.Color] >> out_color

        in_strength >> normal_map[SocketName.Strength]
        imgtex[SocketName.Color] >> normal_map[SocketName.Color]
        normal_map[SocketName.Normal] >> out_normal

    

    def check_image_type(self, layout):
        pass


    def draw_buttons(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        super().draw_buttons(context, layout)
        layout.template_ID(self, "image_ptr", open="image.open", new="image.new")
        #layout.prop(self, "image_type", text="Type")
        #self.check_image_type(layout)
        #layout.prop(self, "uv_map")
        #uv1hint = getattr(context.space_data.id, MaterialProperties.UV1_HINT)
        #layout.label(text=f"UV Map Index: {1 if uv1hint in self.uv_map else 0}")



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
        
        ngb.create_vector_input("UV", True)
        ngb.create_vector_input("Scale", default_value=(1.0,1.0,1.0), subtype="XYZ", dimensions=2)
        #ngb.create_float_input("Scale V", default_value=1.0, range=None, subtype=None)
        ngb.create_vector_output("UV")

        inputs, outputs = ngb._create_io()

        #vec = ngb.create_node(NodeName.CombineXYZ)
        mul = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)

        #ngb.link(inputs, 1, vec, 0)
        #ngb.link(inputs, 2, vec, 1)

        ngb.link(inputs, 0, mul, 0)
        ngb.link(inputs, 1, mul, 1)
        ngb.link(mul, 0, outputs)



class BeamUVAnimation(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}UVAnimation"
    bl_label = "BNG UV Animation"
    bl_nclass = "OP_VECTOR"
    ng_color_tag = GroupColorTag.VECTOR


    class Sockets(StrEnum):
        pass


    class WaveType(StrEnum):
        NONE = "None"
        SIN = "Sin"
        SQUARE = "Square"
        TRIANGLE = "Triangle"


    @staticmethod
    def create_inputs(ngb: NodeGroupBuilder):

        ngb.panel("Rotation Animation")
        ngb.create_vector_input("Rotation Pivot Offset", dimensions=2)
        ngb.create_float_input("Rotation Speed")

        ngb.panel("Scroll Animation")
        ngb.create_vector_input("Scroll UV", dimensions=2)
        ngb.create_float_input("Scroll Speed")

        ngb.panel("Wave Animation")
        ngb.create_menu_input("Wave Type")
        ngb.create_bool_input("Wave Scale")
        ngb.create_float_input("Wave Amplitude")
        ngb.create_float_input("Wave Frequency")

        ngb.panel("Image Sequence")
        ngb.create_float_input("Frames Sec")
        ngb.create_float_input("Frames")


    def create_node_group(self, ngb: NodeGroupBuilder):
        
        ngb.create_vector_input("UV", True)
        ngb.create_vector_output("UV")

        BeamUVAnimation.create_inputs(ngb)

        inputs, outputs = ngb._create_io()

        time = ngb.create_node(NodeName.SceneTime)
        _WT = BeamUVAnimation.WaveType
        switch = ngb.create_menu_switch(SocketType.Float, _WT.NONE, _WT.SIN, _WT.SQUARE, _WT.TRIANGLE)
        ngb.link(inputs, "Wave Type", switch, 0)


    def post_init(self):
        self.inputs["Wave Type"].default_value = BeamUVAnimation.WaveType.NONE
    






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


    def post_init(self):
        self.inputs["Strength"].display_shape = VALUE_SOCKET_SHAPE
        self.inputs["Base"].display_shape = TEXTURE_SOCKET_SHAPE
        self.inputs["Detail"].display_shape = TEXTURE_SOCKET_SHAPE
        self.outputs["Result"].display_shape = TEXTURE_SOCKET_SHAPE


    def create_node_group(self, ngb: NodeGroupBuilder):

        ngb.create_float_input("Strength")
        ngb.create_color_input("Base", True, default_value=(1.0,1.0,1.0,1.0))
        ngb.create_color_input("Detail", True, default_value=(0.5,0.5,0.5,1.0))

        ngb.create_color_output("Result")

        inputs, outputs = ngb._create_io()

        separate = ngb.create_node(NodeName.SeparateColor, mode='HSV')
        greater = ngb.create_math(Operation.GREATER_THAN, value1=0.5)

        light_multiply = ngb.create_math(Operation.MULTIPLY, value1=1.0)
        light_vm_sub  = ngb.create_node(NodeName.VectorMath, operation=Operation.SUBTRACT)
        light_vm_sub.inputs[1].default_value = (0.5,0.5,0.5)
        light_vm_mul  = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)
        light_vm_add  = ngb.create_node(NodeName.VectorMath, operation=Operation.ADD)

        def create_mix(mode: str):
            mix = ngb.create_node(
                NodeName.Mix,
                data_type = Operation.RGBA,
                blend_type = mode,
                clamp_factor = False,
                clamp_result = False,
            )
            bpy.context.view_layer.update()
            return mix
        
        mix = create_mix(Operation.MIX)
        dark = create_mix(Operation.LINEAR_LIGHT)

        ngb.link(light_vm_sub, 0, light_vm_mul, 0)
        ngb.link(light_vm_mul, 0, light_vm_add, 0)

        ngb.link(inputs, 0, dark, 0)
        ngb.link(inputs, 0, light_multiply, 0)
        ngb.link(light_multiply, 0, light_vm_mul, 1)

        ngb.link(inputs, 1, dark, SocketIndex.MixColorIn0)
        ngb.link(inputs, 1, light_vm_add, 1)

        ngb.link(inputs, 2, dark, SocketIndex.MixColorIn1)
        ngb.link(inputs, 2, light_vm_sub, 0)
        ngb.link(inputs, 2, separate, 0)

        ngb.link(separate, 2, greater, 0)
        ngb.link(greater, 0, mix, 0)
        ngb.link(dark, SocketIndex.MixColorOut, mix, SocketIndex.MixColorIn0)
        ngb.link(light_vm_add, 0, mix, SocketIndex.MixColorIn1)

        ngb.link(mix, SocketIndex.MixColorOut, outputs, 0)



class BeamDetailNormal(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}DetailNormal"
    bl_label = "BNG Detail Normal"
    bl_nclass = "OP_VECTOR"
    ng_color_tag = GroupColorTag.VECTOR


    def create_node_group(self, ngb: NodeGroupBuilder):
        
        base = ngb.nc.node(BeamNormalOrDefault, ngb.input(_NORMAL, "Base"))
        detail = ngb.nc.node(BeamNormalOrDefault, ngb.input(_NORMAL, "Detail"))
        neutral = ngb.nc.node(bpy.types.ShaderNodeNormalMap)
        (base + (neutral - detail)) >> ngb.output(_NORMAL, "Normal")



class BeamBSDFCollision(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BSDFCollision"
    bl_label = "BNG Collision BSDF"
    bl_icon = 'MOD_PHYSICS'
    bl_nclass = "SHADER"
    bl_width_default = 200
    ng_color_tag = GroupColorTag.SHADER


    def create_node_group(self, ngb: NodeGroupBuilder):

        Display = "Debug Display"
        ngb.create_bool_input(Display)
        ngb.create_shader_output(SocketName.BSDF)

        inputs, outputs = ngb._create_io()
        diffuse = ngb.create_node(NodeName.BsdfDiffuse)
        transparent = ngb.create_node(NodeName.BsdfTransparent)
        mix = ngb.create_node(NodeName.MixShader)

        diffuse.inputs[SocketName.Color].default_value = (1,0,1,1)

        ngb.link(inputs, 0, mix, 0)
        ngb.link(transparent, 0, mix, 1)
        ngb.link(diffuse, 0, mix, 2)
        ngb.link(mix, 0, outputs, 0)



class BeamNormalOrDefault(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}NormalOrDefault"
    bl_label = "NormalOrDefault"
    ng_color_tag = GroupColorTag.INPUT


    def create_node_group(self, ngb):

        value = ngb.input(_NORMAL, SocketName.Normal)
        
        length = ngb.nc.math(Operation.LENGTH, value)[SocketName.Value]
        is_empty = ngb.nc.math(Operation.COMPARE, length, 0, 0)
        default = ngb.nc.node(bpy.types.ShaderNodeNewGeometry)[SocketName.Normal]

        result = ngb.nc.mix(is_empty, value, default)
        result >> ngb.output(_NORMAL, SocketName.Normal)



class BeamInvertBackfaceNormal(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}InvertBackfaceNormal"
    bl_label = "Invert Backface Normal"
    ng_color_tag = GroupColorTag.VECTOR


    def create_node_group(self, ngb):

        two_sided = ngb.input(_NORMAL, SocketName.Normal)
        do_invert = ngb.input(_BOOL_VALUE, SocketName.InvertBackfaceNormals, default_value=True)
        inverse = two_sided * (-1.0,-1.0,-1.0)

        is_backfacing = ngb.nc.node(NodeName.Geometry)[SocketName.Backfacing]
        one_sided = ngb.nc.mix(is_backfacing, two_sided, inverse)

        result = ngb.nc.mix(do_invert, one_sided, two_sided)
        result >> ngb.output(_NORMAL, SocketName.Normal)



class BeamNormals(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}NormalMap"
    bl_label = "BNG Normal Map"
    ng_color_tag = GroupColorTag.VECTOR


    def create_node_group(self, ngb: NodeGroupBuilder):

        ngb.create_color_input("Base", hide_value=True)
        ngb.create_float_input("Base Strength")
        ngb.create_color_input("Detail", hide_value=True)
        ngb.create_float_input("Detail Strength")
        ngb.create_vector_output("Normal")

        inputs, outputs = ngb._create_io()



class BaseBeamRGBA(BaseShaderNode):

    color: bpy.props.FloatVectorProperty(
        subtype='COLOR', size=4,
        default=(1.0, 1.0, 1.0, 1.0),
        min=0.0, max=1.0,
        update=lambda self, ctx: self.update_color(ctx)
    )


    @property
    def inputs_rgb(self) -> bpy.types.NodeSocketColor: return self.inputs["RGB"]


    @property
    def input_a(self) -> bpy.types.NodeSocketColor: return self.inputs["A"]


    def update_color(self, ctx):
        self.post_init()


    def post_init(self):
        self.inputs_rgb.default_value = self.color
        self.input_a.default_value = self.color[3]
        self.inputs_rgb.hide = True
        self.input_a.hide = True


    def draw_buttons(self, context, layout: bpy.types.UILayout):
        layout.prop(self, "color", text="")



def _RGBA_seperate(ngb: NodeGroupBuilder, value):
    return ngb.nc.seperate_bundle(RGBA, value)

def _RGBA_default(ngb: NodeGroupBuilder, value, default_value = COLOR_WHITE):
    return ngb.nc.node(BeamRGBADefault, value, color=default_value)

def _RGBA_input(ngb: NodeGroupBuilder, name: str, default_value: tuple | None = None, sci = _RGBA_VALUE):
    value = ngb.input(sci, name)
    if default_value is None:
        return _RGBA_seperate(ngb, value)
    else:
        return _RGBA_seperate(ngb, _RGBA_default(ngb, value, default_value))

def _RGBA_combine(ngb: NodeGroupBuilder, color, alpha):
    return ngb.nc.combine_bundle(RGBA, color, alpha, True)

def _RGBA_output(ngb: NodeGroupBuilder, name: str, color, alpha):
    _RGBA_combine(ngb, color, alpha) >> ngb.output(SocketType.Bundle, name)



class BeamRGBA(BaseBeamRGBA):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Input"
    bl_label = "BNG RGBA"
    ng_color_tag = GroupColorTag.INPUT


    def create_node_group(self, ngb: NodeGroupBuilder):

        _RGBA_output(ngb, "RGBA", ngb.input(_COLOR, "RGB"), ngb.input(_FLOAT, "A"))



class BeamRGBAMix(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Mix"
    bl_label = "BNG RGBA Mix"
    ng_color_tag = GroupColorTag.COLOR


    def create_node_group(self, ngb: NodeGroupBuilder):

        factor = ngb.input(_FLOAT, "Factor")
        
        a = _RGBA_input(ngb, "A")
        b = _RGBA_input(ngb, "B")

        color_mix = ngb.nc.mix(factor, a[0], b[0])
        alpha_mix = ngb.nc.mix(factor, a[1], b[1])

        _RGBA_output(ngb, "Result", color_mix, alpha_mix)



class BeamRGBADefault(BaseBeamRGBA):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Default"
    bl_label = "BNG RGBA Default"
    ng_color_tag = GroupColorTag.INPUT


    def create_node_group(self, ngb: NodeGroupBuilder):

        value = ngb.input(SocketType.Bundle, "Value")
        default = _RGBA_combine(ngb, ngb.input(_COLOR, "RGB"), ngb.input(_FLOAT, "A"))
        factor = _RGBA_seperate(ngb, value)[SocketName.Enabled]
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

        ngb.nc.mix(m > 0.5, dark, light) >> ngb.output(_FLOAT_VALUE, SocketName.Value)



class BeamRGBAMath(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Math"
    bl_label = "BNG RGBA Math"
    ng_color_tag = GroupColorTag.COLOR


    operation: bpy.props.EnumProperty(
        name="Type",
        items=[
            (Operation.ADD, Operation.ADD, ""),
            (Operation.SUBTRACT, Operation.SUBTRACT, ""),
            (Operation.MULTIPLY, Operation.MULTIPLY, ""),
            (Operation.DIVIDE, Operation.DIVIDE, ""),
            (Operation.MINIMUM, Operation.MINIMUM, ""),
            (Operation.MAXIMUM, Operation.MAXIMUM, ""),
            (Operation.OVERLAY, Operation.OVERLAY, ""),
            (Operation.HARD_LIGHT, Operation.HARD_LIGHT, ""),
        ],
        default=Operation.MULTIPLY,
        update=lambda self, ctx: self.init(ctx)
    )


    def get_node_group_name(self):
        return f"{super().get_node_group_name()}_{self.operation}"


    def create_node_group(self, ngb: NodeGroupBuilder):

        b_default_value = (1,1,1,1) if self.operation == Operation.MULTIPLY or self.operation == Operation.DIVIDE else (0,0,0,0)
        a = _RGBA_input(ngb, "A")
        b = _RGBA_input(ngb, "B", b_default_value)

        if self.operation == Operation.OVERLAY:
            _RGBA_output(ngb, "Result", ngb.nc.mix(b[1], a[0], b[0]), a[1])
        elif self.operation == Operation.HARD_LIGHT:
            a_rgb = ngb.nc.node(bpy.types.ShaderNodeSeparateColor, a)
            b_rgb = ngb.nc.node(bpy.types.ShaderNodeSeparateColor, b)
            red = ngb.nc.node(BeamMathHardLight, a_rgb[0], b_rgb[0])
            green = ngb.nc.node(BeamMathHardLight, a_rgb[1], b_rgb[1])
            blue = ngb.nc.node(BeamMathHardLight, a_rgb[2], b_rgb[2])
            color = ngb.nc.node(bpy.types.ShaderNodeCombineColor, red, green, blue)
            alpha = ngb.nc.node(BeamMathHardLight, a[1], b[1])
            _RGBA_output(ngb, "Result", color, alpha)
        else:
            color = ngb.nc.math(self.operation, a[0], b[0]) 
            alpha = ngb.nc.math(self.operation, a[1], b[1]) 
            _RGBA_output(ngb, "Result", color, alpha)


    def draw_buttons(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        super().draw_buttons(context, layout)
        layout.prop(self, "operation", text="")



class BeamBDSF10Basic(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BSDF10Basic"
    bl_label = "BNG 1.0 BNGS"
    bl_icon = 'SHADERFX'
    bl_nclass = "SHADER"
    bl_width_default = 240
    ng_color_tag = GroupColorTag.SHADER


    class Sockets(StrEnum):
        COLOR_MAP = "RGBA Color Map"
        COLOR_FACTOR = "RGBA Color"
        OVERLAY_MAP = "RGBA Overlay Map"
        PALETTE_MAP = "RGBA Palette Map"
        SPECULAR_MAP = "Specular Map"
        SPECULAR_ENABLED = "Specualr Enabled"
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


    def create_node_group(self, ngb: NodeGroupBuilder):

        def rgba_math(a, b, operation = Operation.MULTIPLY): return ngb.nc.node(BeamRGBAMath, a, b, operation = operation)
        def rgba_mix(factor, a, b): return ngb.nc.node(BeamRGBAMix, factor, a, b)
        LS = BeamBDSF10Basic.Sockets

        # io
        in_rgba_cm = ngb.input(_RGBA_TEXTURE, LS.COLOR_MAP)
        in_rgba_cf = ngb.input(_RGBA_VALUE, LS.COLOR_FACTOR)
        in_ic_enabled = ngb.input(_BOOL_VALUE, SocketName.InstanceColor) 
        in_vc_enabled = ngb.input(_BOOL_VALUE, SocketName.VertexColor) 
        in_normal_map = ngb.input(_NORMAL, SocketName.Normal)
        out_result = ngb.output(SocketType.Closure, SocketName.BNGShader)

        ngb.panel("Detail")
        in_detail_color = ngb.input(_RGBA_TEXTURE, LS.DETAIL_COLOR)
        in_detail_normal = ngb.input(_NORMAL, SocketName.DetailNormal)
        ngb.panel("Advanced")
        rgba_rm = ngb.input(_RGBA_TEXTURE, LS.RM)
        rm_factor = ngb.input(_FLOAT_VALUE, LS.RM_FACTOR)
        overlay = ngb.input(_RGBA_TEXTURE, LS.OVERLAY_MAP)
        ngb.input(_RGBA_TEXTURE, LS.PALETTE_MAP)
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

        object_info = ngb.nc.node(bpy.types.ShaderNodeObjectInfo)
        vc_info = ngb.nc.node(bpy.types.ShaderNodeVertexColor)

        ic = _RGBA_combine(ngb, object_info[SocketName.Color], object_info[SocketName.Alpha])
        vc = _RGBA_combine(ngb, vc_info[SocketName.Color], vc_info[SocketName.Alpha])


        rgba = _RGBA_default(ngb, in_rgba_cm, COLOR_WHITE)
        rgba = rgba_math(rgba, _RGBA_default(ngb, in_detail_color, COLOR_NULL_HALF), Operation.HARD_LIGHT)
        rgba = rgba_math(rgba, in_rgba_cf)
        rgba = rgba_mix(in_ic_enabled, rgba, rgba_math(rgba, ic))
        rgba = rgba_mix(in_vc_enabled, rgba, rgba_math(rgba, vc))
        rgba = ngb.nc.node(BeamRGBAMath, rgba, overlay, operation = Operation.OVERLAY)

        normal = ngb.nc.node(BeamInvertBackfaceNormal, ngb.nc.node(BeamDetailNormal, in_normal_map, in_detail_normal), closure[SocketName.InvertBackfaceNormals])

        rgba_bundle = _RGBA_seperate(ngb, rgba)
        color = rgba_bundle[SocketName.Color]
        gamma = ngb.nc.node(bpy.types.ShaderNodeGamma, color, 2.2)
        alpha = rgba_bundle[SocketName.Alpha]
        alpha *= opacity_map
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

        rgba_rm_bundle = _RGBA_seperate(ngb, rgba_rm)
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



class BeamBSDF15Detail(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BNGS15Detail"
    bl_label = "BNG 1.5 Detail"
    bl_width_default = 240
    ng_color_tag = GroupColorTag.SHADER


    def create_node_group(self, ngb):
        pass



class BeamBSDF15(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BSDF"
    bl_label = "BNG 1.5 BNGS"
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
        

    def create_node_group(self, ngb: NodeGroupBuilder):

        inputs, outputs = ngb._create_io()
        
        ngb.create_color_input(SocketName.BaseColor)
        ngb.create_float_input(SocketName.Metallic, default_value=0.0)
        ngb.create_float_input(SocketName.Roughness, default_value=0.5)
        ngb.create_float_input(SocketName.Alpha)
        ngb.create_vector_input(SocketName.Normal, True)
        ngb.create_float_input(SocketName.AmbientOcclusion, True)
        ngb.create_closure_output(SocketName.BNGShader)

        ngb.panel("Advanced")
        ngb.create_color_input(SocketName.Palette, True)
        ngb.create_color_input(SocketName.Emissive, default_value=(0,0,0,1))
        ngb.create_float_input(SocketName.ClearCoat, default_value=0)
        ngb.create_float_input(SocketName.ClearCoatRoughness, default_value=1)


        closure = ngb.create_closure(BNGS_IO)
        principled = ngb.create_node(NodeName.BsdfPrincipled)
        principled.inputs[SocketName.ThinWall].default_value = True
        principled.inputs[SocketName.SubsurfaceAnisotropy].default_value = 1.0
        principled.inputs[SocketName.EmissionStrength].default_value = 1.0
        ao_scale = ngb.create_node(NodeName.VectorMath, [None, (0.5,0.5,0.5), (0.5,0.5,0.5)], operation=Operation.MULTIPLY_ADD)
        ao_mix = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)
        invert_backface_normal = ngb.create_node(BeamInvertBackfaceNormal.bl_idname)

        ngb.link(inputs, SocketName.Normal, invert_backface_normal)
        ngb.link(closure.input, SocketName.InvertBackfaceNormals, invert_backface_normal)
        ngb.link(closure.input, SocketName.SubsurfaceScattering, principled, SocketName.SubsurfaceWeight)

        ngb.link(inputs, SocketName.AmbientOcclusion, ao_scale, 0)
        ngb.link(inputs, SocketName.BaseColor, ao_mix, 0)
        ngb.link(ao_scale, 0, ao_mix, 1)
        ngb.link(ao_mix, 0, principled, SocketName.BaseColor)

        ngb.link(invert_backface_normal, SocketName.Normal, principled)
        ngb.link(invert_backface_normal, SocketName.Normal, principled, SocketName.CoatNormal)

        ngb.link(inputs, SocketName.Metallic, principled)
        ngb.link(inputs, SocketName.Roughness, principled)
        ngb.link(inputs, SocketName.Emissive, principled, SocketName.EmissionColor)
        ngb.link(inputs, SocketName.ClearCoat, principled, SocketName.CoatWeight)
        ngb.link(inputs, SocketName.ClearCoatRoughness, principled, SocketName.CoatRoughness)

        ngb.link(principled, SocketName.BSDF, closure.output, SocketName.Shader)
        ngb.link(inputs, SocketName.Alpha, closure.output)

        ngb.link(closure.output, SocketName.Closure, outputs, SocketName.BNGShader)
        


class BeamStageMix(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}StageMix"
    bl_label = "BNG Stage Mix 1.5"
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

_ReflectionMode_INT_DICT: dict[ReflectionMode, int] = {
    ReflectionMode.NONE: 0,
    ReflectionMode.LEVEL: 1,
    ReflectionMode.CUBEMAP: 2,
}



class BeamMaterial(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}Material"
    bl_label = "BNG Material"
    bl_icon = "MATERIAL"
    bl_nclass = "SHADER"
    bl_width_default = 200
    ng_color_tag = GroupColorTag.SHADER


    reflection_mode: bpy.props.EnumProperty(
        name="Reflection Mode",
        items=[
            (ReflectionMode.NONE, ReflectionMode.NONE, ""),
            (ReflectionMode.LEVEL, ReflectionMode.LEVEL, ""),
            (ReflectionMode.CUBEMAP, ReflectionMode.CUBEMAP, ""),
        ],
        default=ReflectionMode.NONE,
        update=lambda self, ctx: self.update_reflection_mode(ctx)
    )
    reflection_cubemap: bpy.props.StringProperty(name="Cubemap", default="none")


    class Sockets(StrEnum):
        CLIP = "Alpha Clip"
        CLIP_T = "Alpha Clip Threshold"
        BLEND = "Alpha Blend"
        DOUBLE_SIDED = "Double Sided"
        INVERT_BACKFACE_NORMALS = SocketName.InvertBackfaceNormals
        SHADOWS = "Cast Shadows"
        SUBSURFACE_SCATTERING = SocketName.SubsurfaceScattering


    def update_reflection_mode(self, ctx: bpy.types.Context):
        input: bpy.types.NodeSocketInt = self.inputs[SocketName.ReflectionMode]
        input.default_value = _ReflectionMode_INT_DICT.get(self.reflection_mode)


    def draw_buttons(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        super().draw_buttons(context, layout)
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "reflection_mode")
        if self.reflection_mode == ReflectionMode.CUBEMAP:
            layout.prop(self, "reflection_cubemap")


    def post_init(self):
        LS = BeamMaterial.Sockets
        self.inputs[LS.CLIP].display_shape = VALUE_SOCKET_SHAPE
        self.inputs[LS.CLIP_T].display_shape = VALUE_SOCKET_SHAPE
        self.inputs[LS.BLEND].display_shape = VALUE_SOCKET_SHAPE
        self.inputs[LS.DOUBLE_SIDED].display_shape = VALUE_SOCKET_SHAPE
        self.inputs[LS.INVERT_BACKFACE_NORMALS].display_shape = VALUE_SOCKET_SHAPE
        self.inputs[LS.SHADOWS].display_shape = VALUE_SOCKET_SHAPE
        self.inputs[LS.SUBSURFACE_SCATTERING].display_shape = VALUE_SOCKET_SHAPE
        self.inputs[SocketName.ReflectionMode].hide = True


    def create_node_group(self, ngb: NodeGroupBuilder):
        
        LS = BeamMaterial.Sockets

        in_bngs = ngb.input(SocketType.Closure, SocketName.BNGShader)

        in_clip = ngb.input(_BOOL_VALUE, LS.CLIP)
        in_clip_t = ngb.input(_FLOAT_VALUE, LS.CLIP_T, default_value=0.5)
        in_blend = ngb.input(_BOOL_VALUE, LS.BLEND)
        in_ds = ngb.input(_BOOL_VALUE, LS.DOUBLE_SIDED)
        in_ibn = ngb.input(_BOOL_VALUE, LS.INVERT_BACKFACE_NORMALS, default_value=True)
        in_shadows_enabled = ngb.input(_BOOL_VALUE, LS.SHADOWS, default_value=True)
        in_ss = ngb.input(_FLOAT_VALUE, LS.SUBSURFACE_SCATTERING, default_value=0.0)
        in_rmode = ngb.input(_INT_PRIVATE, SocketName.ReflectionMode, default_value=0)
        output = ngb.output(SocketType.Shader, SocketName.Shader)

        eval = ngb.nc.eval_closure(BNGS_IO)
        in_bngs >> eval[SocketName.Closure]
        in_ibn >> eval[SocketName.InvertBackfaceNormals]
        in_rmode >> eval[SocketName.ReflectionMode]
        in_ss >> eval[SocketName.SubsurfaceScattering]

        shader = eval[SocketName.Shader]
        alpha = eval[SocketName.Alpha]

        geometry = ngb.nc.node(bpy.types.ShaderNodeNewGeometry)
        backface_enabled = in_ds | ngb.nc.bool(geometry[SocketName.Backfacing], True)
        light_path = ngb.nc.node(bpy.types.ShaderNodeLightPath)
        shadows_enabled = in_shadows_enabled | ngb.nc.bool(light_path[SocketName.IsShadowRay])
        discard = backface_enabled & shadows_enabled

        clip_t = alpha > in_clip_t
        clip_enabled = clip_t | ngb.nc.bool(in_clip, True)
        clip_factor = clip_enabled & discard

        blend_factor = eval[SocketName.Alpha] | in_blend

        transparent = ngb.nc.node(bpy.types.ShaderNodeBsdfTransparent)
        mix_blend = ngb.nc.mix(blend_factor, transparent, shader)
        mix_clip = ngb.nc.mix(clip_factor, transparent, mix_blend)

        mix_clip >> output



class ShaderNodeTree(bpy.types.Menu):

    bl_idname = "GRILLEBEAMNG_MT_ShaderNodeTree"
    bl_label = "BeamNG"
    tree_type = NodeName.ShaderNodeTree
    node_items = [
        "Material V1.5",
        BeamBSDF15,
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
    ]


    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == cls.tree_type


    def draw(self, context):

        layout = self.layout
        for item in self.node_items:

            if item is None:
                layout.separator()
                continue

            elif isinstance(item, str):
                layout.label(text=item, icon="REMOVE")

            else:
                op = layout.operator("node.add_node", text=item.bl_label)
                op.type = item.bl_idname
                op.use_transform = True


    @staticmethod
    def addmenu_append(self: 'ShaderNodeTree', context: bpy.types.Context):
        tree_type = context.space_data.tree_type
        if tree_type != ShaderNodeTree.tree_type:
            return
        self.layout.menu(ShaderNodeTree.bl_idname)



class ShaderNodeRegistry:

    nodes = [
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
    ]


    @staticmethod
    def register():
        for cls in ShaderNodeRegistry.nodes:
            bpy.utils.register_class(cls)

        bpy.utils.register_class(ShaderNodeTree)
        bpy.types.NODE_MT_add.append(ShaderNodeTree.addmenu_append)


    @staticmethod
    def unregister():
        bpy.types.NODE_MT_add.remove(ShaderNodeTree.addmenu_append)
        bpy.utils.unregister_class(ShaderNodeTree)

        for cls in ShaderNodeRegistry.nodes:
            bpy.utils.unregister_class(cls)