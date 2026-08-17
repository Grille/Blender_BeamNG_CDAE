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
SHADER_NODE_PREFIX = "ShaderNodeCustom.grille_beamng_cdae_"

BNG_SHADER = _Signature(
    _Signature.Socket(SocketName.Shader, SocketType.Shader),
    _Signature.Socket(SocketName.Alpha, SocketType.Float)
)
RGBA =_Signature(
    _Signature.Socket(SocketName.Color, SocketType.Color),
    _Signature.Socket(SocketName.Alpha, SocketType.Float),
    _Signature.Socket(SocketName.Enabled, SocketType.Bool),
)

BNGS_INPUT = _Signature(
    _Signature.Socket(SocketName.InvertBackfaceNormals, SocketType.Bool),
    _Signature.Socket(SocketName.ReflectionEnabled, SocketType.Bool),
    _Signature.Socket(SocketName.SubsurfaceScattering, SocketType.Float)
)
BNGS_OUTPUT = _Signature(
    _Signature.Socket(SocketName.Shader, SocketType.Shader),
    _Signature.Socket(SocketName.Alpha, SocketType.Float)
)
BNGS_IO = _Signature.IO(BNGS_INPUT, BNGS_OUTPUT)

TEXTURE_SOCKET_SHAPE = SocketShape.SQUARE
VALUE_SOCKET_SHAPE = SocketShape.DIAMOND

COLOR_WHITE = (1,1,1,1)
COLOR_BLACK = (0,0,0,0)

SCI_FLOAT = _SCI.FACTOR
SCI_FLOAT_VALUE = _SCI(SocketType.Float, VALUE_SOCKET_SHAPE, False, default_value=1, **_SCI.FACTOR.kwargs)
SCI_FLOAT_TEXTURE = _SCI(SocketType.Float, TEXTURE_SOCKET_SHAPE, True, default_value=1)
SCI_COLOR = _SCI.COLOR
SCI_COLOR_VALUE = _SCI(SocketType.Color, VALUE_SOCKET_SHAPE, False, default_value=COLOR_WHITE)
SCI_COLOR_TEXTURE = _SCI(SocketType.Color, TEXTURE_SOCKET_SHAPE, True, default_value=COLOR_WHITE)



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
        self.update_alpha_link_lock: bool = False
        self.messages: list[str] = []



class BaseShaderNode(bpy.types.ShaderNodeCustomGroup):

    bl_label = "BNG Node"
    bl_icon = 'NONE'
    tree_type = NodeName.ShaderNodeTree
    ng_color_tag: GroupColorTag = GroupColorTag.NONE
    ng_version: int = 0
    ng_shared: bool = True


    @property
    def runtime(self) -> NodeRuntimeData:
        return NodeRuntimeData.get_instance(self)


    @classmethod
    def poll(cls, ntree: bpy.types.NodeTree):
        return ntree.bl_idname == NodeName.ShaderNodeTree
    

    def get_validator(self):
        return NodeLayoutValidator(self, None, self.runtime.messages)


    def init(self, context):
        tree = self.node_tree = self.get_node_group()

        if NODE_GROUP_JSON_KEY in tree:
            ngdata =  NodeGroupData.from_text(tree[NODE_GROUP_JSON_KEY])
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
        return f"{self.bl_idname}_v{self.ng_version}"

    
    def get_node_group(self):
        group_name = self.get_node_group_name()

        if self.ng_shared and group_name in bpy.data.node_groups:
            return bpy.data.node_groups[group_name]
        
        ngb = NodeGroupBuilder(group_name)
        self.create_node_group(ngb)
        ngb.arrange_nodes()
        tree = ngb.tree
        tree.color_tag = self.ng_color_tag
        tree[NODE_GROUP_JSON_KEY] = ngb.ngdata.dump()
        return tree


    def create_node_group(self, ngb: NodeGroupBuilder):
        pass



class BeamImageTex(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}TexImg"
    bl_label = "BNG Image Texture"
    bl_icon = 'TEXTURE'

    bl_width_default = 240
    color_tag = GroupColorTag.TEXTURE

    _updating = False


    class ImageType(StrEnum):
        COLOR = "Color"
        COLOR_HDR = "Color_HDR"
        NORMAL = "Normal"
        DATA = "Data"
        SRGB = "sRGB"
        NON_COLOR = "Non-Color"

    ImageType_Dict = {
        ImageType.COLOR: ImageType.SRGB,
        ImageType.COLOR_HDR: ImageType.NON_COLOR,
        ImageType.NORMAL: ImageType.NON_COLOR,
        ImageType.DATA: ImageType.NON_COLOR,
    }


    # Custom properties
    image_ptr: bpy.props.PointerProperty(type=bpy.types.Image, update=lambda self, ctx: self.update_image(ctx))
    image_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            (ImageType.COLOR, "Color", "sRGB"),
            (ImageType.COLOR_HDR, "Color HDR", "Non-Color"),
            (ImageType.NORMAL, "Normal", "Non-Color"),
            (ImageType.DATA, "Data", "Non-Color"),
        ],
        default=ImageType.COLOR_HDR,
        update=lambda self, ctx: self.update_type(ctx)
    )
    uv_map: bpy.props.EnumProperty(
        name="UV Map",
        items=lambda self, context: self.uv_map_items(context),
        update=lambda self, context: self.update_uvmap(context),
    )


    @property
    def image(self) -> bpy.types.Image: return self.image_ptr


    def get_teximage(self) -> bpy.types.ShaderNodeTexImage:
        return self.node_tree.nodes.get(NodeName.TexImage)


    def get_node_group_by_name(self, group_name: str):

        if group_name in bpy.data.node_groups:
            return bpy.data.node_groups[group_name]
        
        cls = type(self)
        ngb = NodeGroupBuilder(group_name)
        cls.create_node_group(ngb, self.image)
        ngb.arrange_nodes()
        tree = ngb.tree
        tree.color_tag = cls.color_tag
        return tree
    

    def update_image(self, ctx):

        group_name = self.get_node_group_image_name()

        if self.node_tree.name == group_name:
            return

        self.node_tree = self.get_node_group_by_name(group_name)

        #self.update_type(ctx)


    def update_type(self, ctx):

        ImageType = BeamImageTex.ImageType

        teximage = self.get_teximage()
        if teximage.image is None:
            return
        
        match self.image_type:
            case ImageType.COLOR:
                self.outputs["Color"].enabled

        
        cs = teximage.image.colorspace_settings
        if self.image_type == ImageType.COLOR and cs.name != ImageType.SRGB:
            cs.name = ImageType.SRGB
        elif cs.name != ImageType.NON_COLOR:
            cs.name = ImageType.NON_COLOR

            
    def uv_map_items(self, context):
        # Find active object with mesh data
        obj = context.object
        if not obj or not obj.type == 'MESH':
            return [("UVMap", "UVMap", "Default UV Map")]

        items = []
        for uv in obj.data.uv_layers:
            items.append((uv.name, uv.name, ""))
        return items or [("UVMap", "UVMap", "Default UV Map")]


    def update_uvmap(self, context):
        # Update the UV Map node's uv_map property when dropdown changes
        if self.node_tree:
            for node in self.node_tree.nodes:
                if node.bl_idname == NodeName.UVMap:
                    node.uv_map = self.uv_map


    def get_node_group_image_name(self):
        return f".{self.bl_idname}_{self.image.name_full}_v{self.node_group_version}"
    

    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder, image: bpy.types.Image | None = None):
        
        ngb.create_vector_input(SocketName.UV, True)
        ngb.create_color_output(SocketName.Color)
        ngb.create_float_output(SocketName.Alpha)
        ngb.create_vector_output(SocketName.Normal)
        ngb.create_float_output(SocketName.Data)

        inputs, outputs = ngb.create_io()
        imgtex: bpy.types.ShaderNodeTexImage = ngb.create_node(NodeName.TexImage)
        imgtex.name = NodeName.TexImage
        imgtex.image = image
        normal_map = ngb.create_node(NodeName.NormalMap)

        ngb.link(inputs, SocketName.UV, imgtex)
        ngb.link(imgtex, SocketName.Color, normal_map)
        ngb.link(normal_map, SocketName.Normal, outputs)
        ngb.link(imgtex, SocketName.Color, outputs, SocketName.Data)
        ngb.link(imgtex, SocketName.Color, outputs, 0)
        ngb.link(imgtex, SocketName.Alpha, outputs, 1)
    

    def check_image_type(self, layout):

        teximage = self.get_teximage()
        if not teximage or not teximage.image:
            return
        
        cs_name: str = teximage.image.colorspace_settings.name

        if BeamImageTex.ImageType_Dict[self.image_type].value != cs_name:
            row = layout.row()
            row.alert = True
            row.label(text=f"Color space mismatch! ({cs_name})")


    def draw_buttons(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        super().draw_buttons(context, layout)
        layout.template_ID(self, "image_ptr", open="image.open", new="image.new")
        layout.prop(self, "image_type", text="Type")
        self.check_image_type(layout)
        #layout.prop(self, "uv_map")
        #uv1hint = getattr(context.space_data.id, MaterialProperties.UV1_HINT)
        #layout.label(text=f"UV Map Index: {1 if uv1hint in self.uv_map else 0}")



class BeamFactorColor(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}FactorColor"
    bl_label = "BNG Factor (Color)"
    bl_nclass = "OP_COLOR"
    ng_color_tag = GroupColorTag.COLOR


    def create_node_group(self, ngb: NodeGroupBuilder):
        
        texture = ngb.io.input(SCI_COLOR_TEXTURE, SocketName.TextureMap)
        factor = ngb.io.input(SCI_COLOR_VALUE, SocketName.Factor)

        result = ngb.io.output(SCI_COLOR, "Result")

        ngb.create_panel("Advanced")
        vc = ngb.io.input(SCI_COLOR_VALUE, SocketName.VertexColor)
        ic = ngb.io.input(SCI_COLOR_VALUE, SocketName.InstanceColor)

        texture * factor * vc * ic >> result


        
class BeamFactorFloat(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}FactorFloat"
    bl_label = "BNG Factor (Data)"
    bl_nclass = "CONVERTER"
    ng_color_tag = GroupColorTag.CONVERTER


    def create_node_group(self, ngb: NodeGroupBuilder):
        ngb.io.input(SCI_FLOAT_TEXTURE, SocketName.TextureMap) * ngb.io.input(SCI_FLOAT_VALUE, SocketName.Factor) >> ngb.io.output(SCI_FLOAT, "Result")



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

        inputs, outputs = ngb.create_io()

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

        ngb.create_panel("Rotation Animation")
        ngb.create_vector_input("Rotation Pivot Offset", dimensions=2)
        ngb.create_float_input("Rotation Speed")

        ngb.create_panel("Scroll Animation")
        ngb.create_vector_input("Scroll UV", dimensions=2)
        ngb.create_float_input("Scroll Speed")

        ngb.create_panel("Wave Animation")
        ngb.create_menu_input("Wave Type")
        ngb.create_bool_input("Wave Scale")
        ngb.create_float_input("Wave Amplitude")
        ngb.create_float_input("Wave Frequency")

        ngb.create_panel("Image Sequence")
        ngb.create_float_input("Frames Sec")
        ngb.create_float_input("Frames")


    def create_node_group(self, ngb: NodeGroupBuilder):
        
        ngb.create_vector_input("UV", True)
        ngb.create_vector_output("UV")

        BeamUVAnimation.create_inputs(ngb)

        inputs, outputs = ngb.create_io()

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

        inputs, outputs = ngb.create_io()

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
        
        ngb.create_vector_input("Base", True)
        ngb.create_vector_input("Detail", True)

        ngb.create_vector_output("Normal")

        inputs, outputs = ngb.create_io()

        normal: bpy.types.ShaderNodeNormalMap = ngb.create_node(NodeName.NormalMap)
        math_sub = ngb.create_node(NodeName.VectorMath, operation=Operation.SUBTRACT)
        math_add = ngb.create_node(NodeName.VectorMath, operation=Operation.ADD)

        BeamNormalOrDefault.create(ngb, inputs, 1, math_sub, 0)
        ngb.link(normal, 0, math_sub, 1)
        BeamNormalOrDefault.create(ngb, inputs, 0, math_add, 0)
        ngb.link(math_sub, 0, math_add, 1)
        ngb.link(math_add, 0, outputs)



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

        inputs, outputs = ngb.create_io()
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

        ngb.create_vector_input(SocketName.Normal, True)
        ngb.create_vector_output(SocketName.Normal)
        inputs, outputs = ngb.create_io()

        length = ngb.create_node(NodeName.VectorMath, operation=Operation.LENGTH)
        compare = ngb.create_math(Operation.COMPARE, 0, 0, 0)
        geometry = ngb.create_node(NodeName.Geometry)
        mix_by_normal_enabled = ngb.create_node(NodeName.Mix, data_type = Operation.VECTOR)

        ngb.link(inputs, SocketName.Normal, length, 0)
        ngb.link(length, SocketName.Value, compare, 0)

        ngb.link(compare, 0, mix_by_normal_enabled, SocketIndex.MixFactor)
        ngb.link(geometry, SocketName.Normal, mix_by_normal_enabled, SocketIndex.MixVectorIn1)
        ngb.link(inputs, SocketName.Normal, mix_by_normal_enabled, SocketIndex.MixVectorIn0)

        ngb.link(mix_by_normal_enabled, SocketIndex.MixVectorOut, outputs, SocketName.Normal)


    @staticmethod
    def create(ngb: NodeGroupBuilder, node0: bpy.types.ShaderNode, socket0: str | int, node1: bpy.types.ShaderNode = None, socket1: str | int = None):
        node: BeamNormalOrDefault = ngb.create_node(BeamNormalOrDefault.bl_idname)
        ngb.link(node0, socket0, node, 0)
        if node1 is not None: ngb.link(node, 0, node1, socket1)
        return node



class BeamInvertBackfaceNormal(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}InvertBackfaceNormal"
    bl_label = "Invert Backface Normal"
    ng_color_tag = GroupColorTag.VECTOR


    def create_node_group(self, ngb):

        ngb.create_vector_input(SocketName.Normal, True)
        ngb.create_bool_input(SocketName.InvertBackfaceNormals, False, default_value=True)
        ngb.create_vector_output(SocketName.Normal)
        inputs, outputs = ngb.create_io()

        geometry = ngb.create_node(NodeName.Geometry)
        invert_normal = ngb.create_node(NodeName.VectorMath, [None, (-1.0,-1.0,-1.0)], operation=Operation.MULTIPLY)
        mix_by_backface = ngb.create_node(NodeName.Mix, data_type = Operation.VECTOR)
        mix_by_invert_enabled = ngb.create_node(NodeName.Mix, data_type = Operation.VECTOR)
        input_normal = BeamNormalOrDefault.create(ngb, inputs, SocketName.Normal)
        
        ngb.link(input_normal, 0, invert_normal, 0)

        ngb.link(geometry, SocketName.Backfacing, mix_by_backface, SocketIndex.MixFactor)
        ngb.link(input_normal, 0, mix_by_backface, SocketIndex.MixVectorIn0)
        ngb.link(invert_normal, 0, mix_by_backface, SocketIndex.MixVectorIn1)

        ngb.link(inputs, SocketName.InvertBackfaceNormals, mix_by_invert_enabled, SocketIndex.MixFactor)
        ngb.link(mix_by_backface, SocketIndex.MixVectorOut, mix_by_invert_enabled, SocketIndex.MixVectorIn0)
        ngb.link(input_normal, 0, mix_by_invert_enabled, SocketIndex.MixVectorIn1)

        ngb.link(mix_by_invert_enabled, SocketIndex.MixVectorOut, outputs, SocketName.Normal)



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

        inputs, outputs = ngb.create_io()



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



class BeamRGBA(BaseBeamRGBA):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Input"
    bl_label = "BNG RGBA"
    ng_color_tag = GroupColorTag.INPUT


    def create_node_group(self, ngb: NodeGroupBuilder):

        rgb = ngb.io.input(SCI_COLOR, "RGB")
        a = ngb.io.input(SCI_FLOAT, "A")
        rgba = ngb.io.output(SocketType.Bundle, "RGBA")

        ngb.nc.combine_bundle(RGBA, rgb, a, True) >> rgba



class BeamRGBAMix(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Mix"
    bl_label = "BNG RGBA Mix"
    ng_color_tag = GroupColorTag.COLOR


    def create_node_group(self, ngb: NodeGroupBuilder):

        factor = ngb.io.input(_SCI.FACTOR, "Factor")
        
        def binput(name: str): return ngb.nc.seperate_bundle(RGBA, ngb.io.input(SocketType.Bundle, name))
        a = binput("A")
        b = binput("B")

        color_mix = ngb.nc.mix(a[0], b[0], factor)
        alpha_mix = ngb.nc.mix(a[1], b[1], factor)

        result = ngb.io.output(SocketType.Bundle, "Result")
        ngb.nc.combine_bundle(RGBA, color_mix, alpha_mix, True) >> result



class BeamRGBADefault(BaseBeamRGBA):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Default"
    bl_label = "BNG RGBA Default"
    ng_color_tag = GroupColorTag.INPUT


    def create_node_group(self, ngb: NodeGroupBuilder):

        ngb.create_bundle_input("Value")
        ngb.create_color_input("RGB")
        ngb.create_float_input("A")
        ngb.create_bundle_output("RGBA")

        inputs, outputs = ngb.create_io()

        default = ngb.create_node(BeamRGBA.bl_idname)
        ngb.link(inputs, "RGB", default)
        ngb.link(inputs, "A", default)

        mix = ngb.create_node(BeamRGBAMix.bl_idname)
        #value = ngb.seperate_bundle(RGBA, _NS(inputs, 0)) #------------------!!!!!!!!!!
        #ngb.link(value, SocketName.Enabled, mix, 0)
        ngb.link(default, 0, mix, 1)
        ngb.link(inputs, "Value", mix, 2)
        ngb.link(mix, 0, outputs)


    @staticmethod
    def create(ngb: NodeGroupBuilder, default_value: tuple = (1,1,1,1), node0: bpy.types.ShaderNode = None, socket0: str | int = 0, node1: bpy.types.ShaderNode = None, socket1: str | int = None):
        node: BeamRGBADefault = ngb.create_node(BeamRGBADefault.bl_idname)
        node.color = default_value
        if node0 is not None: ngb.link(node0, socket0, node, 0)
        if node1 is not None: ngb.link(node, 0, node1, socket1)
        return node



class BeamRGBAMath(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}RGBA_Math"
    bl_label = "BNG RGBA Math"
    ng_color_tag = GroupColorTag.COLOR


    class ImageType(StrEnum):
        COLOR = "Color"
        COLOR_HDR = "Color_HDR"
        NORMAL = "Normal"
        DATA = "Data"
        SRGB = "sRGB"
        NON_COLOR = "Non-Color"

    ImageType_Dict = {
        ImageType.COLOR: ImageType.SRGB,
        ImageType.COLOR_HDR: ImageType.NON_COLOR,
        ImageType.NORMAL: ImageType.NON_COLOR,
        ImageType.DATA: ImageType.NON_COLOR,
    }


    # Custom properties
    image_ptr: bpy.props.PointerProperty(type=bpy.types.Image, update=lambda self, ctx: self.update_image(ctx))
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
        ],
        default=Operation.MULTIPLY,
        update=lambda self, ctx: self.init(ctx)
    )


    def get_node_group_name(self):
        return f"{super().get_node_group_name()}_{self.operation}"


    def create_node_group(self, ngb: NodeGroupBuilder):

        ngb.create_bundle_input("A")
        ngb.create_bundle_input("B")
        ngb.create_bundle_output("Result")

        inputs, outputs = ngb.create_io()

        # if self.operation == Operation.OVERLAY:
        #     color_mix = ngb.create_node(NodeName.Mix, data_type = Operation.VECTOR)
        #     value0 = ngb.seperate_bundle(RGBA, _NS(inputs, 0), _NS(color_mix, SocketIndex.MixVectorIn0))
        #     ngb.seperate_bundle(RGBA, _NS(inputs, 1), _NS(color_mix, SocketIndex.MixVectorIn1), _NS(color_mix, SocketIndex.MixFactor))
        #     ngb.combine_bundle(RGBA, _NS(outputs, 0), _NS(color_mix, SocketIndex.MixVectorOut), _NS(value0, 1)).inputs[SocketName.Enabled].default_value = True
        # else:
        #     color_mul = ngb.create_node(NodeName.VectorMath, operation=self.operation)
        #     alpha_mul = ngb.create_math(operation=self.operation)
        #     default_value = (1,1,1,1) if self.operation == Operation.MULTIPLY or self.operation == Operation.DIVIDE else (0,0,0,0)
        #     input1_bundle = BeamRGBADefault.create(ngb, default_value, inputs, 1)
        #     input0 = ngb.seperate_bundle(RGBA, _NS(inputs, 0), _NS(color_mul, 0), _NS(alpha_mul, 0))
        #     ngb.seperate_bundle(RGBA, _NS(input1_bundle, 0), _NS(color_mul, 1), _NS(alpha_mul, 1))
        #     ngb.combine_bundle(RGBA, _NS(outputs, 0), _NS(color_mul, 0), _NS(alpha_mul, 0), _NS(input0, 2))


    def draw_buttons(self, context: bpy.types.Context, layout: bpy.types.UILayout):
        super().draw_buttons(context, layout)
        layout.prop(self, "operation", text="")



class BeamBDSF10Basic(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BSDF10Basic"
    bl_label = "BNG 1.0 Basic BSDF"
    bl_icon = 'SHADERFX'
    bl_nclass = "SHADER"
    bl_width_default = 240
    ng_color_tag = GroupColorTag.SHADER


    class Sockets(StrEnum):
        COLOR_MAP = "RGBA Color Map"
        COLOR_FACTOR = "RGBA Color"
        OVERLAY_MAP = "RGBA Color"
        SPECULAR_MAP = "Specular Map"
        SPECULAR_COLOR = "Specular Color"
        SPECULAR_ROUGHNESS = SocketName.Roughness
        RM = "RGBA Reflectivity Map"
        RM_FACTOR = "Reflectivity Map Factor"
        RM_ENABLED = "Reflectivity Map Enabled"
        OPACITY_MAP = "Opacity Map"
        DETAIL_COLOR = "RGBA Detail Color"
        EMISIVE = SocketName.Emissive
        GLOW_COLOR = "Glow Color"

        
    def update(self):
        LS = BeamBDSF10Basic.Sockets
        rm_enabled: bpy.types.NodeSocketBool = self.inputs[LS.RM_ENABLED]
        rm_enabled.default_value = self.inputs[LS.RM].is_linked
        rm_enabled.hide = False


    def create_node_group(self, ngb: NodeGroupBuilder):

        LS = BeamBDSF10Basic.Sockets
        BLACK = (0,0,0,1)

        ngb.create_bundle_input(LS.COLOR_MAP)
        ngb.create_bundle_input(LS.COLOR_FACTOR)
        ngb.create_bool_input(SocketName.VertexColor) 
        ngb.create_vector_input(SocketName.Normal, True)
        ngb.create_closure_output(SocketName.BNGShader)
        
        ngb.create_panel("Advanced")
        ngb.create_bundle_input(LS.RM)
        ngb.create_float_input(LS.RM_FACTOR)
        ngb.create_bundle_input(LS.DETAIL_COLOR)
        ngb.create_vector_input(SocketName.DetailNormal, True)
        ngb.create_panel("Lighting")
        ngb.create_color_input(LS.SPECULAR_COLOR, default_value=BLACK)
        ngb.create_float_input(LS.SPECULAR_MAP, True)
        ngb.create_float_input(LS.SPECULAR_ROUGHNESS)
        ngb.create_color_input(LS.GLOW_COLOR, default_value=BLACK)
        ngb.create_bool_input(LS.EMISIVE)


        inputs, outputs = ngb.create_io()
        closure = ngb.create_closure(BNGS_IO)

        # diffuse = ngb.create_node(NodeName.BsdfDiffuse)
        # metallic = ngb.create_node(NodeName.BsdfMetallic)
        # metallic.inputs[SocketName.Roughness].default_value = 0.0
        # metallic.inputs[SocketName.BaseColor].default_value = (1,1,1,1)
        # metallic.inputs[SocketName.EdgeTint].default_value = (1,1,1,1)
        # mix_shader = ngb.create_node(NodeName.MixShader)
        # mix_rgb = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)
        # mix_alpha = ngb.create_math(Operation.MULTIPLY)
        # mix_reflect = ngb.create_math(Operation.MULTIPLY)
        # invert_backface_normal = ngb.create_node(BeamInvertBackfaceNormal.bl_idname)

        # ngb.link(inputs, SocketName.Normal, invert_backface_normal)
        # ngb.link()

        # ngb.link(inputs, SocketName.BaseColor, mix_rgb, 0)
        # ngb.link(inputs, SocketName.VertexColor, mix_rgb, 1)
        # ngb.link(mix_rgb, 0, diffuse, SocketName.Color)

        # ngb.link(inputs, SocketName.BaseAlpha, mix_alpha, 0)
        # ngb.link(inputs, SocketName.VertexAlpha, mix_alpha, 1)
        # ngb.link(mix_alpha, 0, mix_reflect, 0)
        # ngb.link(inputs, SocketName.ReflectionEnabled, mix_reflect, 1)
        # ngb.link(mix_reflect, 0, mix_shader, 0)

        # ngb.link(invert_backface_normal, SocketName.Normal, diffuse, SocketName.Normal)
        # ngb.link(invert_backface_normal, SocketName.Normal, metallic, SocketName.Normal)
        # ngb.link(diffuse, 0, mix_shader, 1)
        # ngb.link(metallic, 0, mix_shader, 2)

        # ngb.combine_bundle(BNG_SHADER, _NS(outputs), _NS(mix_shader), _NS(mix_alpha))


    def post_init(self):
        LS = BeamBDSF10Basic.Sockets
        self.inputs[LS.RM_ENABLED].hide = True



class BeamBSDF15(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BSDF"
    bl_label = "BNG 1.5 BSDF"
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

        inputs, outputs = ngb.create_io()
        
        ngb.create_color_input(SocketName.BaseColor)
        ngb.create_float_input(SocketName.Metallic, default_value=0.0)
        ngb.create_float_input(SocketName.Roughness, default_value=0.5)
        ngb.create_float_input(SocketName.Alpha)
        ngb.create_vector_input(SocketName.Normal, True)
        ngb.create_float_input(SocketName.AmbientOcclusion, True)
        ngb.create_closure_output(SocketName.BNGShader)

        ngb.create_panel("Advanced")
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
    #bl_icon = 'SHADERFX'


    def post_init(self):
        pass


    def create_node_group(self, ngb: NodeGroupBuilder):

        ngb.create_closure_input("BNGS Base")
        ngb.create_closure_input("BNGS Overlay")

        ngb.create_closure_output(SocketName.BNGShader)

        inputs, outputs = ngb.create_io()

        mix = ngb.create_node(NodeName.MixShader)

        sub = ngb.create_math(Operation.SUBTRACT, value0=1.0)
        mul = ngb.create_math(Operation.MULTIPLY)
        add = ngb.create_math(Operation.ADD)

        sep_base = ngb.create_closure_eval(BNGS_IO)
        ngb.link(inputs, "BNGS Base", sep_base, SocketName.Closure)
        sep_overlay = ngb.create_closure_eval(BNGS_IO)
        ngb.link(inputs, "BNGS Overlay", sep_overlay, SocketName.Closure)

        closure = ngb.create_closure(BNGS_IO)

        ngb.link(closure.input, SocketName.InvertBackfaceNormals, sep_base)
        ngb.link(closure.input, SocketName.SubsurfaceScattering, sep_base)
        ngb.link(closure.input, SocketName.InvertBackfaceNormals, sep_overlay)
        ngb.link(closure.input, SocketName.SubsurfaceScattering, sep_overlay)

        ngb.link(sep_overlay, 1, mix, 0)
        ngb.link(sep_base, 0, mix, 1)
        ngb.link(sep_overlay, 0, mix, 2)

        ngb.link(sep_overlay, 1, sub, 1)
        ngb.link(sep_overlay, 1, add, 1)
        ngb.link(sep_base, 1, mul, 0)

        ngb.link(sub, 0, mul, 1)
        ngb.link(mul, 0, add, 0)

        ngb.link(mix, 0, closure.output, SocketName.Shader)
        ngb.link(add, 0, closure.output, SocketName.Alpha)
        ngb.link(closure.output, SocketName.Closure, outputs, SocketName.BNGShader)



class ReflectionMode(StrEnum):
    NONE = "None"
    LEVEL = "Level"
    CUBEMAP = "Cubemap"



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
        default=ReflectionMode.LEVEL,
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
        input: bpy.types.NodeSocketBool = self.inputs[SocketName.ReflectionEnabled]
        input.default_value = self.reflection_mode != ReflectionMode.NONE


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
        self.inputs[SocketName.ReflectionEnabled].hide = True


    def create_node_group(self, ngb: NodeGroupBuilder):
        
        LS = BeamMaterial.Sockets

        ngb.create_closure_input(SocketName.BNGShader)

        ngb.create_bool_input(LS.CLIP)
        ngb.create_float_input(LS.CLIP_T, default_value=0.5)
        ngb.create_bool_input(LS.BLEND)
        ngb.create_bool_input(LS.DOUBLE_SIDED)
        ngb.create_bool_input(LS.INVERT_BACKFACE_NORMALS, default_value=True)
        ngb.create_bool_input(LS.SHADOWS, default_value=True)
        ngb.create_float_input(LS.SUBSURFACE_SCATTERING, default_value=0.0, range=(0,1))
        ngb.create_bool_input(SocketName.ReflectionEnabled, default_value=True)
        ngb.create_shader_output(SocketName.Shader)

        inputs, outputs = ngb.create_io()

        geometry = ngb.create_node(NodeName.Geometry)
        light_path = ngb.create_node(NodeName.LightPath)

        transparent = ngb.create_node(NodeName.BsdfTransparent)
        mix_blend = ngb.create_node(NodeName.MixShader)
        mix_clip = ngb.create_node(NodeName.MixShader)

        clip_t = ngb.create_math(Operation.GREATER_THAN)
        blend_enabled = ngb.create_math(Operation.MAXIMUM)
        clip_enabled = ngb.create_math(Operation.MAXIMUM)
        backface_enabled = ngb.create_math(Operation.MAXIMUM)
        shadows_enabled = ngb.create_math(Operation.MAXIMUM)
        discard = ngb.create_math(Operation.MINIMUM)
        discard_clip = ngb.create_math(Operation.MINIMUM)

        eval = ngb.create_closure_eval(BNGS_IO)

        ngb.link(inputs, SocketName.BNGShader, eval, SocketName.Closure)
        ngb.link(inputs, LS.INVERT_BACKFACE_NORMALS, eval)
        ngb.link(inputs, SocketName.ReflectionEnabled, eval)
        ngb.link(inputs, LS.SUBSURFACE_SCATTERING, eval)

        ngb.link(transparent, 0, mix_blend, 1)
        ngb.link(transparent, 0, mix_clip, 1)
        ngb.link(eval, SocketName.Shader, mix_blend, 2)
        ngb.link(mix_blend, 0, mix_clip, 2)
        ngb.link(mix_clip, 0, outputs, 0)

        ngb.link(eval, SocketName.Alpha, blend_enabled, 0)
        ngb.link_bool(inputs, LS.BLEND, blend_enabled, 1, True)
        ngb.link(blend_enabled, 0, mix_blend, 0)

        ngb.link(eval, SocketName.Alpha, clip_t, 0)
        ngb.link(inputs, LS.CLIP_T, clip_t, 1)
        ngb.link(clip_t, 0, clip_enabled, 0)
        ngb.link_bool(inputs, LS.CLIP, clip_enabled, 1, True)

        ngb.link_bool(inputs, LS.DOUBLE_SIDED, backface_enabled, 0)
        ngb.link_bool(geometry, SocketName.Backfacing, backface_enabled, 1, True)

        ngb.link_bool(inputs, LS.SHADOWS, shadows_enabled, 0)
        ngb.link_bool(light_path, SocketName.IsShadowRay, shadows_enabled, 1, True)

        ngb.link(backface_enabled, 0, discard, 0)
        ngb.link(shadows_enabled, 0, discard, 1)

        ngb.link(clip_enabled, 0, discard_clip, 0)
        ngb.link(discard, 0, discard_clip, 1)
        ngb.link(discard_clip, 0, mix_clip, 0)



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