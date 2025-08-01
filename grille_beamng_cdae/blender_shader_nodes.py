import bpy
from enum import Enum

# pyright: reportInvalidTypeForm=false



class NodeNames(str, Enum):
    Group = "ShaderNodeGroup"
    GroupInput = "NodeGroupInput"
    GroupOutput = "NodeGroupOutput"
    OutputMaterial = "ShaderNodeOutputMaterial"
    BsdfPrincipled = "ShaderNodeBsdfPrincipled"
    BsdfTransparent = "ShaderNodeBsdfTransparent"
    Mix = "ShaderNodeMix"
    MixRGB = "ShaderNodeMixRGB"
    MixShader = "ShaderNodeMixShader"
    NormalMap = "ShaderNodeNormalMap"
    TexImage = "ShaderNodeTexImage"
    UVMap = "ShaderNodeUVMap"
    ShaderToRGB = "ShaderNodeShaderToRGB"
    SeparateColor = "ShaderNodeSeparateColor"
    Math = "ShaderNodeMath"
    VectorMath = "ShaderNodeVectorMath"
    LightPath = "ShaderNodeLightPath"
    Geometry = "ShaderNodeNewGeometry"
    CombineXYZ = "ShaderNodeCombineXYZ"

    RGB = "ShaderNodeRGB"
    Value = "ShaderNodeValue"



class Sockets(str, Enum):
    Color = "Color"
    BaseColor = "Base Color"
    VertexColor = "Vertex Color"
    Metallic = "Metallic"
    Roughness = "Roughness"
    Alpha = "Alpha"
    Normal = "Normal"

    DetailColor = "Detail Color"
    DetailNormal = "Detail Normal"
    AO = "Ambient Occlusion"

    BSDF = "BSDF"
    Shader = "Shader"

    IsShadowRay = "Is Shadow Ray"
    Backfacing = "Backfacing"



class MathOP(str, Enum):
    SUBTRACT = 'SUBTRACT'
    MULTIPLY = 'MULTIPLY'
    ADD = 'ADD'
    MULTIPLY_ADD = 'MULTIPLY_ADD'
    GREATER_THAN = 'GREATER_THAN'
    LESS_THAN = 'LESS_THAN'
    MINIMUM = 'MINIMUM'
    MAXIMUM = 'MAXIMUM'



class NodeGroupBuilder():

    def __init__(self, idname: str):
        self.ng: bpy.types.ShaderNodeTree = bpy.data.node_groups.new(idname, 'ShaderNodeTree')


    def create_any_input(self, name: str, type: str, hide_value: bool = False, default_value = None):
        input: bpy.types.NodeSocket = self.ng.interface.new_socket(name, in_out='INPUT', socket_type=f"NodeSocket{type}")
        input.hide_value = hide_value
        if default_value is not None:
            input.default_value = default_value
        return input
    

    def create_float_input(self, name: str, hide_value = False, default_value: float = 1.0):
        input: bpy.types.NodeSocketFloat = self.create_any_input(name, "Float", hide_value)
        input.min_value = 0.0
        input.max_value = 1.0
        input.subtype = "FACTOR"
        input.default_value = default_value
        return input
    

    def create_bool_input(self, name: str, hide_value = False, default_value = False):
        input = self.create_any_input(name, "Bool", hide_value)
        input.default_value = default_value
        return input
    

    def create_color_input(self, name: str, hide_value = False, default_value = (1.0,1.0,1.0,1.0)):
        input = self.create_any_input(name, "Color", hide_value)
        input.default_value = default_value
        return input
    

    def create_vector_input(self, name: str, hide_value = False):
        input = self.create_any_input(name, "Vector", hide_value)
        return input
    

    def create_shader_input(self, name: str, hide_value = False):
        input = self.create_any_input(name, "Shader", hide_value)
        return input
    

    def create_any_output(self, name: str, type: str):
        output = self.ng.interface.new_socket(name, in_out='OUTPUT', socket_type=f"NodeSocket{type}")
        return output
    

    def create_float_output(self, name: str):
        return self.create_any_output(name, "Float")
    

    def create_color_output(self, name: str):
        return self.create_any_output(name, "Color")
    

    def create_vector_output(self, name: str):
        return self.create_any_output(name, "Vector")
    

    def create_shader_output(self, name: str):
        return self.create_any_output(name, "Shader")
    

    def create_node(self, type: str, op: str = None) -> bpy.types.ShaderNode:
        node = self.ng.nodes.new(type)
        if op is not None: node.operation = op
        return node
    

    def create_math(self, operation: str, value0: float = None, value1: float = None):
            node: bpy.types.ShaderNodeMath = self.create_node(NodeNames.Math, op=operation)
            if value0 is not None: node.inputs[0].default_value = value0
            if value1 is not None: node.inputs[1].default_value = value1
            return node
    

    def create_io(self):
        inputs = self.create_node(NodeNames.GroupInput)
        outputs = self.create_node(NodeNames.GroupOutput)
        return (inputs, outputs)
    

    def link(self, node0: bpy.types.ShaderNode, socket0: str | int, node1: bpy.types.ShaderNode, socket1: str | int = None): 
        if socket1 is None: socket1 = socket0

        try:
            out_socket = node0.outputs[socket0]
            in_socket = node1.inputs[socket1]
        except (KeyError, IndexError, AttributeError) as e:
            raise ValueError(f"Invalid socket index or name: {e}")

        if not out_socket.is_output or in_socket.is_output:
            raise ValueError("Sockets are not output/input as expected.")
        
        print(f"link {out_socket.name} to {in_socket.name}")
    
        self.ng.links.new(node0.outputs[socket0], node1.inputs[socket1])


    def link_bool(self, node0: bpy.types.ShaderNode, socket0: str | int, node1: bpy.types.ShaderNode, socket1: str | int = None, invert = False):
        op = MathOP.LESS_THAN if invert else MathOP.GREATER_THAN
        math = self.create_math(op, value1=0.5)
        self.link(node0, socket0, math, 0)
        self.link(math, 0, node1, socket1)



class BaseShaderNode(bpy.types.ShaderNodeCustomGroup):

    bl_label = "BNG Node"
    bl_icon = 'NONE'
    tree_type = "ShaderNodeTree"
    default_width = 150


    def init(self, context):
        self.node_tree = self.get_node_group()
        self.width = self.default_width


    def draw_buttons(self, context, layout):
        pass
        #layout.prop(self, 'Colors', text='')
    

    @classmethod 
    def get_node_group(cls):
        idname = f".{cls.bl_idname}"

        if idname in bpy.data.node_groups:
            return bpy.data.node_groups[idname]
        
        ngb = NodeGroupBuilder(idname)
        cls.create_node_group(ngb)
        return ngb.ng
    

    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        pass



class BeamFactorColor(BaseShaderNode):

    bl_idname = "ShaderNodeCustom.grille_beamng_cdae_FactorColor"
    bl_label = "BNG Factor (Color)"


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        
        ngb.create_color_input("Texture Map", True)
        ngb.create_color_input("Factor", False)

        ngb.create_color_output("Result")

        inputs, outputs = ngb.create_io()

        mul = ngb.create_node(NodeNames.VectorMath, op=MathOP.MULTIPLY)

        ngb.link(inputs, 0, mul, 0)
        ngb.link(inputs, 1, mul, 1)
        ngb.link(mul, 0, outputs)


        
class BeamFactorFloat(BaseShaderNode):

    bl_idname = "ShaderNodeCustom.grille_beamng_cdae_FactorFloat"
    bl_label = "BNG Factor"


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        
        ngb.create_float_input("Texture Map", True)
        ngb.create_float_input("Factor", False)

        ngb.create_float_output("Result")

        inputs, outputs = ngb.create_io()

        mul = ngb.create_math(MathOP.MULTIPLY)

        ngb.link(inputs, 0, mul, 0)
        ngb.link(inputs, 1, mul, 1)
        ngb.link(mul, 0, outputs)


class BeamDetailUVScale(BaseShaderNode):

    bl_idname = "ShaderNodeCustom.grille_beamng_cdae_DetailUVSCale"
    bl_label = "BNG Detail UV Scale"


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        
        ngb.create_vector_input("UV", True)
        ngb.create_any_input("Scale U", "Float", default_value=1.0)
        ngb.create_any_input("Scale V", "Float", default_value=1.0)
        ngb.create_vector_output("UV")

        inputs, outputs = ngb.create_io()

        vec = ngb.create_node(NodeNames.CombineXYZ)
        mul = ngb.create_node(NodeNames.VectorMath, op=MathOP.MULTIPLY)

        ngb.link(inputs, 1, vec, 0)
        ngb.link(inputs, 2, vec, 1)

        ngb.link(inputs, 0, mul, 0)
        ngb.link(vec, 0, mul, 1)
        ngb.link(mul, 0, outputs)



class BeamDetailColor(BaseShaderNode):

    bl_idname = "ShaderNodeCustom.grille_beamng_cdae_DetailColor"
    bl_label = "BNG Detail Color"


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):

        ngb.create_float_input("Strength")
        ngb.create_color_input("Base")
        ngb.create_color_input("Detail", True, default_value=(0.5,0.5,0.5,1.0))

        ngb.create_color_output("Color")

        inputs, outputs = ngb.create_io()

        separate = ngb.create_node(NodeNames.SeparateColor)
        separate.mode = 'HSV'

        multiply = ngb.create_node(NodeNames.Math)
        multiply.operation = 'MULTIPLY'
        multiply.inputs[1].default_value = 4.0

        greater = ngb.create_node(NodeNames.Math)
        greater.operation = 'GREATER_THAN'
        greater.inputs[1].default_value = 0.5

        def create_mix(mode: str):
            mix = ngb.create_node(NodeNames.Mix)
            mix.data_type = 'RGBA'
            mix.blend_type = mode
            mix.clamp_factor = False
            mix.clamp_result = False
            bpy.context.view_layer.update()
            return mix
        
        mix = create_mix("MIX")
        light = create_mix("LINEAR_LIGHT")
        overlay = create_mix("OVERLAY")
        
        ngb.link(inputs, 0, light, 0)
        ngb.link(inputs, 0, multiply, 0)
        ngb.link(multiply, 0, overlay, 0)

        ngb.link(inputs, 1, light, 6)
        ngb.link(inputs, 1, overlay, 6)

        ngb.link(inputs, 2, light, 7)
        ngb.link(inputs, 2, overlay, 7)
        ngb.link(inputs, 2, separate, 0)

        ngb.link(separate, 2, greater, 0)
        ngb.link(greater, 0, mix, 0)
        ngb.link(light, 2, mix, 6)
        ngb.link(overlay, 2, mix, 7)

        ngb.link(mix, 2, outputs, 0)



class BeamDetailNormal(BaseShaderNode):

    bl_idname = "ShaderNodeCustom.grille_beamng_cdae_DetailNormal"
    bl_label = "BNG Detail Normal"


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        
        ngb.create_vector_input("Base", True)
        ngb.create_vector_input("Detail", True)

        ngb.create_vector_output("Normal")

        inputs, outputs = ngb.create_io()

        math_add = ngb.create_node(NodeNames.VectorMath, op=MathOP.ADD)

        ngb.link(inputs, 0, math_add, 0)
        ngb.link(inputs, 1, math_add, 1)
        ngb.link(math_add, 0, outputs)



class BeamBSDF15(BaseShaderNode):

    bl_idname = "ShaderNodeCustom.grille_beamng_cdae_BSDF"
    bl_label = "BNG BSDF 1.5"
    bl_icon = 'SHADERFX'
    default_width = 250

    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):

        ngb.create_color_input(Sockets.BaseColor)
        ngb.create_color_input(Sockets.VertexColor, True) 
        ngb.create_float_input(Sockets.Metallic, default_value=0.0)
        ngb.create_float_input(Sockets.Roughness, default_value=0.5)
        ngb.create_float_input(Sockets.Alpha)
        ngb.create_vector_input(Sockets.Normal, True)
        ngb.create_float_input(Sockets.AO, True)

        ngb.create_shader_output(Sockets.BSDF)
        ngb.create_float_output(Sockets.Alpha)

        inputs, outputs = ngb.create_io()
        principled = ngb.create_node(NodeNames.BsdfPrincipled)
        mix_vtx = ngb.create_node(NodeNames.VectorMath, MathOP.MULTIPLY)

        ao_scale = ngb.create_node(NodeNames.VectorMath, MathOP.MULTIPLY_ADD)
        ao_scale.inputs[1].default_value = (0.5,0.5,0.5)
        ao_scale.inputs[2].default_value = (0.5,0.5,0.5)

        ao_mix = ngb.create_node(NodeNames.VectorMath, MathOP.MULTIPLY)

        ngb.link(inputs, Sockets.AO, ao_scale, 0)
        ngb.link(inputs, Sockets.BaseColor, mix_vtx, 0)
        ngb.link(inputs, Sockets.VertexColor, mix_vtx, 1)
        ngb.link(mix_vtx, 0, ao_mix, 0)
        ngb.link(ao_scale, 0, ao_mix, 1)
        ngb.link(ao_mix, 0, principled, Sockets.BaseColor)

        ngb.link(inputs, Sockets.Metallic, principled)
        ngb.link(inputs, Sockets.Roughness, principled)
        ngb.link(inputs, Sockets.Normal, principled)

        ngb.link(principled, Sockets.BSDF, outputs)
        ngb.link(inputs, Sockets.Alpha, outputs)
    


class BeamStageMix(BaseShaderNode):

    bl_idname = "ShaderNodeCustom.grille_beamng_cdae_StageMix"
    bl_label = "BNG Stage Mix"
    bl_icon = 'SHADERFX'
    default_width = 200

    def create_node_group(ngb: NodeGroupBuilder):

        ngb.create_shader_input("Base")
        ngb.create_float_input("Base.Alpha", True, default_value=1)
        ngb.create_shader_input("Overlay")
        ngb.create_float_input("Overlay.Alpha", True, default_value=0)

        ngb.create_shader_output(Sockets.Shader)
        ngb.create_float_output(Sockets.Alpha)

        inputs, outputs = ngb.create_io()

        mix = ngb.create_node(NodeNames.MixShader)

        sub = ngb.create_math(MathOP.SUBTRACT, value0=1.0)
        mul = ngb.create_math(MathOP.MULTIPLY)
        add = ngb.create_math(MathOP.ADD)

        ngb.link(inputs, 3, mix, 0)
        ngb.link(inputs, 0, mix, 1)
        ngb.link(inputs, 2, mix, 2)
        ngb.link(mix, 0, outputs, 0)

        ngb.link(inputs, 3, sub, 1)
        ngb.link(inputs, 3, add, 1)
        ngb.link(inputs, 1, mul, 0)

        ngb.link(sub, 0, mul, 1)
        ngb.link(mul, 0, add, 0)

        ngb.link(add, 0, outputs, 1)



class BeamMaterial(BaseShaderNode):

    bl_idname = "ShaderNodeCustom.grille_beamng_cdae_Material"
    bl_label = "BNG Material"
    bl_icon = "MATERIAL"
    default_width = 200


    class Sockets(str, Enum):
        CLIP = "Alpha Clip"
        CLIP_T = "Alpha Clip Threshold"
        BLEND = "Alpha Blend"
        DS = "Double Sided"
        IBN = "Invert Backface Normals"
        SHADOWS = "Cast Shadows"


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        
        LS = BeamMaterial.Sockets

        ngb.create_shader_input(Sockets.Shader)
        ngb.create_float_input(Sockets.Alpha, True)

        ngb.create_bool_input(LS.CLIP)
        ngb.create_float_input(LS.CLIP_T, default_value = 0)
        ngb.create_bool_input(LS.BLEND)
        ngb.create_bool_input(LS.DS)
        ngb.create_bool_input(LS.IBN)
        ngb.create_bool_input(LS.SHADOWS, default_value=True)
        ngb.create_shader_output(Sockets.Shader)

        inputs, outputs = ngb.create_io()

        geometry = ngb.create_node(NodeNames.Geometry)
        light_path = ngb.create_node(NodeNames.LightPath)

        transparent = ngb.create_node(NodeNames.BsdfTransparent)
        mix_blend = ngb.create_node(NodeNames.MixShader)
        mix_clip = ngb.create_node(NodeNames.MixShader)

        clip_t = ngb.create_math(MathOP.GREATER_THAN)
        blend_enabled = ngb.create_math(MathOP.MAXIMUM)
        clip_enabled = ngb.create_math(MathOP.MAXIMUM)
        backface_enabled = ngb.create_math(MathOP.MAXIMUM)
        shadows_enabled = ngb.create_math(MathOP.MAXIMUM)
        discard = ngb.create_math(MathOP.MINIMUM)
        discard_clip = ngb.create_math(MathOP.MINIMUM)

        ngb.link(transparent, 0, mix_blend, 1)
        ngb.link(transparent, 0, mix_clip, 1)
        ngb.link(inputs, Sockets.Shader, mix_blend, 2)
        ngb.link(mix_blend, 0, mix_clip, 2)
        ngb.link(mix_clip, 0, outputs, 0)

        ngb.link(inputs, Sockets.Alpha, blend_enabled, 0)
        ngb.link_bool(inputs, LS.BLEND, blend_enabled, 1, True)
        ngb.link(blend_enabled, 0, mix_blend, 0)

        ngb.link(inputs, Sockets.Alpha, clip_t, 0)
        ngb.link(inputs, LS.CLIP_T, clip_t, 1)
        ngb.link(clip_t, 0, clip_enabled, 0)
        ngb.link_bool(inputs, LS.CLIP, clip_enabled, 1, True)

        ngb.link_bool(inputs, LS.DS, backface_enabled, 0)
        ngb.link_bool(geometry, Sockets.Backfacing, backface_enabled, 1, True)

        ngb.link_bool(inputs, LS.SHADOWS, shadows_enabled, 0)
        ngb.link_bool(light_path, Sockets.IsShadowRay, shadows_enabled, 1, True)

        ngb.link(backface_enabled, 0, discard, 0)
        ngb.link(shadows_enabled, 0, discard, 1)

        ngb.link(clip_enabled, 0, discard_clip, 0)
        ngb.link(discard, 0, discard_clip, 1)
        ngb.link(discard_clip, 0, mix_clip, 0)



class ShaderNodeTree(bpy.types.Menu):
    bl_idname = "GRILLEBEAMNG_MT_ShaderNodeTree"
    bl_label = "BeamNG"
    tree_type = "ShaderNodeTree"
    node_items = [BeamBSDF15, BeamStageMix, BeamMaterial, None, BeamFactorColor, BeamFactorFloat, BeamDetailUVScale, BeamDetailColor, BeamDetailNormal]


    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == cls.tree_type


    def draw(self, context):

        layout = self.layout
        for item in self.node_items:

            if item is None:
                layout.separator()
                continue

            else:
                op = layout.operator("node.add_node", text=item.bl_label)
                op.type = item.bl_idname
                op.use_transform = True


    @staticmethod
    def addmenu_append(self, context):
        tree_type = context.space_data.tree_type
        if tree_type != ShaderNodeTree.tree_type:
            return
        self.layout.menu(ShaderNodeTree.bl_idname)


    @staticmethod
    def register_nodes():
        for cls in ShaderNodeTree.node_items:
            if cls is not None:
                bpy.utils.register_class(cls)


    @staticmethod
    def unregister_nodes():
        for cls in ShaderNodeTree.node_items:
            if cls is not None:
                bpy.utils.unregister_class(cls)
