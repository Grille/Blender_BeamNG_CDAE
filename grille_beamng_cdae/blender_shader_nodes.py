import bpy
from enum import Enum

from .blender_material_properties import *
from .blender_enums import *
from .blender_shader_nodes_utils import *

# pyright: reportInvalidTypeForm=false


SHADER_NODE_PREFIX = "ShaderNodeCustom.grille_beamng_cdae_"



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


    @property
    def runtime(self) -> NodeRuntimeData:
        return NodeRuntimeData.get_instance(self)


    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == NodeName.ShaderNodeTree
    

    def update_alpha_link(self, key: str, alpha_key: str):
        if self.runtime.update_alpha_link_lock:
            return
        
        self.runtime.update_alpha_link_lock = True

        try:
        
            shader_input = self.inputs[key]
            alpha_input = self.inputs[alpha_key]

            if not shader_input.is_linked:
                if alpha_input.is_linked:
                    for link in list(alpha_input.links):
                        self.id_data.links.remove(link)
                return
            
            link = shader_input.links[0]
            from_node = link.from_node
            from_socket = link.from_socket

            out_sockets = from_node.outputs
            try:
                socket_idx = out_sockets.find(from_socket.name)
                if socket_idx == -1:
                    return
                next_idx = socket_idx + 1
                if next_idx >= len(out_sockets):
                    return
                next_socket = out_sockets[next_idx]
            except Exception:
                return

            # If already linked to the correct socket, skip
            already_linked = (
                alpha_input.is_linked
                and alpha_input.links[0].from_socket == next_socket
            )
            if already_linked:
                return

            # Remove existing links
            for l in list(alpha_input.links):
                self.id_data.links.remove(l)

            # Create the new link
            self.id_data.links.new(next_socket, alpha_input)

        finally:

            self.runtime.update_alpha_link_lock = False


    def init(self, context):
        self.node_tree = self.get_node_group()
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
    

    @classmethod 
    def get_node_group(cls):
        idname = f".{cls.bl_idname}"

        if idname in bpy.data.node_groups:
            return bpy.data.node_groups[idname]
        
        ngb = NodeGroupBuilder(idname)
        cls.create_node_group(ngb)
        ngb.ng.color_tag = "SHADER"
        return ngb.ng
    

    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        pass



class BeamImageTex(bpy.types.ShaderNodeCustomGroup):

    bl_idname = f"{SHADER_NODE_PREFIX}TexImg"
    bl_label = "BNG Image Texture"
    bl_icon = 'TEXTURE'

    bl_width_default = 240
    _updating = False


    class ImageType(str, Enum):
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
    image: bpy.props.PointerProperty(type=bpy.types.Image, update=lambda self, ctx: self.update_image(ctx))
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


    def get_teximage(self) -> bpy.types.ShaderNodeTexImage:
        return self.node_tree.nodes.get(NodeName.TexImage)


    def update_image(self, ctx):

        image_node = self.get_teximage()
        image_node.image = self.image
        self.bl_label = self.image.name
        self.update_type(ctx)


    def update_type(self, ctx):

        ImageType = BeamImageTex.ImageType

        teximage = self.get_teximage()
        if teximage.image is None:
            return
        
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


    def create_node_group(self):
        
        idname = f".{self.bl_idname}"
        ngb = NodeGroupBuilder(idname)

        ngb.create_any_input("Scale U", "Float", default_value=1.0)
        ngb.create_any_input("Scale V", "Float", default_value=1.0)
        ngb.create_color_output("Color")
        ngb.create_float_output("Alpha")

        inputs, outputs = ngb.create_io()
        uv_map = ngb.create_node(NodeName.UVMap)
        scale = ngb.create_node(BeamDetailUVScale.bl_idname)
        imgtex = ngb.create_node(NodeName.TexImage)
        imgtex.name = NodeName.TexImage

        ngb.link(uv_map, 0, scale, 0)
        ngb.link(inputs, 0, scale, 1)
        ngb.link(inputs, 1, scale, 2)

        ngb.link(scale, 0, imgtex, 0)

        ngb.link(imgtex, 0, outputs, 0)
        ngb.link(imgtex, 1, outputs, 1)

        self.node_tree = ngb.ng
    

    def init(self, context):
        print("init")
        self.create_node_group()
        self.width = self.default_width


    def copy(self, node):
        print("copy")
        self.node_tree.clear()# = node.node_tree.copy()


    def check_image_type(self, layout):

        teximage = self.get_teximage()
        if not teximage or not teximage.image:
            return
        
        cs_name: str = teximage.image.colorspace_settings.name

        if BeamImageTex.ImageType_Dict[self.image_type].value != cs_name:
            row = layout.row()
            row.alert = True
            row.label(text=f"Color space mismatch! ({cs_name})")


    def draw_buttons(self, context, layout):
        layout.template_ID(self, "image", open="image.open", new="image.new")
        layout.prop(self, "image_type", text="Type")
        self.check_image_type(layout)
        layout.prop(self, "uv_map")
        uv1hint = getattr(context.space_data.id, MaterialProperties.UV1_HINT)
        layout.label(text=f"UV Map Index: {1 if uv1hint in self.uv_map else 0}")



class BeamFactorColor(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}FactorColor"
    bl_label = "BNG Factor (Color)"
    bl_nclass = "OP_COLOR"


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        
        ngb.create_color_input("Texture Map", True)
        ngb.create_color_input("Factor", False)
        
        ngb.create_color_output("Result")

        ngb.create_panel("Advanced")
        ngb.create_color_input(SocketName.VertexColor, True, default_value=(1,1,1,1))
        ngb.create_color_input(SocketName.InstanceColor, True, default_value=(1,1,1,1))

        inputs, outputs = ngb.create_io()

        mul = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)
        mul_ic = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)
        mul_vc = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)

        ngb.link(inputs, 0, mul, 0)
        ngb.link(inputs, 1, mul, 1)

        ngb.link(mul, 0, mul_vc, 0)
        ngb.link(inputs, SocketName.VertexColor, mul_vc, 1)

        ngb.link(mul_vc, 0, mul_ic, 0)
        ngb.link(inputs, SocketName.InstanceColor, mul_ic, 1)

        ngb.link(mul_ic, 0, outputs)


        
class BeamFactorFloat(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}FactorFloat"
    bl_label = "BNG Factor"
    bl_nclass = "CONVERTER"


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        
        ngb.create_float_input("Texture Map", True)
        ngb.create_float_input("Factor", False)

        ngb.create_float_output("Result")

        inputs, outputs = ngb.create_io()

        mul = ngb.create_math(Operation.MULTIPLY)

        ngb.link(inputs, 0, mul, 0)
        ngb.link(inputs, 1, mul, 1)
        ngb.link(mul, 0, outputs)



class BeamDetailUVScale(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}DetailUVSCale"
    bl_label = "BNG Detail UV Scale"
    bl_nclass = "OP_VECTOR"


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        
        ngb.create_vector_input("UV", True)
        ngb.create_float_input("Scale U", default_value=1.0, range=None, subtype=None)
        ngb.create_float_input("Scale V", default_value=1.0, range=None, subtype=None)
        ngb.create_vector_output("UV")

        inputs, outputs = ngb.create_io()

        vec = ngb.create_node(NodeName.CombineXYZ)
        mul = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)

        ngb.link(inputs, 1, vec, 0)
        ngb.link(inputs, 2, vec, 1)

        ngb.link(inputs, 0, mul, 0)
        ngb.link(vec, 0, mul, 1)
        ngb.link(mul, 0, outputs)



class BeamDetailColor(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}DetailColor"
    bl_label = "BNG Detail Color"
    bl_nclass = "OP_COLOR"


    def update(self):
        messages = self.runtime.messages
        messages.clear()
        nlv = NodeLayoutValidator(self)

        if nlv.try_follow(1):
            if nlv.is_node_idname(BeamFactorColor.bl_idname):
                messages.append("- Base:")
                messages.append(f"{BeamFactorColor.bl_label} must come after {BeamDetailColor.bl_label}")


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):

        ngb.create_float_input("Strength")
        ngb.create_color_input("Base", True, default_value=(1.0,1.0,1.0,1.0))
        ngb.create_color_input("Detail", True, default_value=(0.5,0.5,0.5,1.0))

        ngb.create_color_output("Color")

        inputs, outputs = ngb.create_io()

        separate = ngb.create_node(NodeName.SeparateColor, mode='HSV')
        greater = ngb.create_math(Operation.GREATER_THAN, value1=0.5)

        light_multiply = ngb.create_math(Operation.MULTIPLY, value1=4.0)
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


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        
        ngb.create_vector_input("Base", True)
        ngb.create_vector_input("Detail", True)

        ngb.create_vector_output("Normal")

        inputs, outputs = ngb.create_io()

        math_add = ngb.create_node(NodeName.VectorMath, operation=Operation.ADD)

        ngb.link(inputs, 0, math_add, 0)
        ngb.link(inputs, 1, math_add, 1)
        ngb.link(math_add, 0, outputs)



class BeamBSDFCollision(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BSDFCollision"
    bl_label = "BNG Collision BSDF"
    bl_icon = 'MOD_PHYSICS'
    bl_nclass = "SHADER"
    bl_width_default = 200

    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):

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



class BeamBDSF10Basic(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BSDF10Basic"
    bl_label = "BNG 1.0 Basic BSDF"
    bl_icon = 'SHADERFX'
    bl_nclass = "SHADER"
    bl_width_default = 240


    def post_init(self):
        super().post_init()
        self.inputs[SocketName.VertexColor].hide = True
        self.inputs[SocketName.VertexAlpha].hide = True


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):

        ngb.create_color_input(SocketName.BaseColor)
        ngb.create_float_input(SocketName.BaseAlpha)
        ngb.create_color_input(SocketName.VertexColor, True) 
        ngb.create_float_input(SocketName.VertexAlpha, True)
        ngb.create_vector_input(SocketName.Normal, True)
        ngb.create_bool_input(SocketName.ReflectionEnabled)

        ngb.create_shader_output(SocketName.BSDF)
        ngb.create_float_output(SocketName.Alpha)

        inputs, outputs = ngb.create_io()
        diffuse = ngb.create_node(NodeName.BsdfDiffuse)
        metallic = ngb.create_node(NodeName.BsdfMetallic)
        metallic.inputs[SocketName.Roughness].default_value = 0.0
        metallic.inputs[SocketName.BaseColor].default_value = (1,1,1,1)
        metallic.inputs[SocketName.EdgeTint].default_value = (1,1,1,1)
        mix_shader = ngb.create_node(NodeName.MixShader)
        mix_rgb = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)
        mix_alpha = ngb.create_math(Operation.MULTIPLY)
        mix_reflect = ngb.create_math(Operation.MULTIPLY)

        ngb.link(inputs, SocketName.BaseColor, mix_rgb, 0)
        ngb.link(inputs, SocketName.VertexColor, mix_rgb, 1)
        ngb.link(mix_rgb, 0, diffuse, SocketName.Color)

        ngb.link(inputs, SocketName.BaseAlpha, mix_alpha, 0)
        ngb.link(inputs, SocketName.VertexAlpha, mix_alpha, 1)
        ngb.link(mix_alpha, 0, mix_reflect, 0)
        ngb.link(inputs, SocketName.ReflectionEnabled, mix_reflect, 1)
        ngb.link(mix_reflect, 0, mix_shader, 0)

        ngb.link(inputs, SocketName.Normal, diffuse, SocketName.Normal)
        ngb.link(inputs, SocketName.Normal, metallic, SocketName.Normal)
        ngb.link(diffuse, 0, mix_shader, 1)
        ngb.link(metallic, 0, mix_shader, 2)

        ngb.link(mix_shader, 0, outputs, SocketName.BSDF)
        ngb.link(mix_alpha, 0, outputs, SocketName.Alpha)



class BeamBSDF15(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}BSDF"
    bl_label = "BNG 1.5 BSDF"
    bl_icon = 'SHADERFX'
    bl_nclass = "SHADER"
    bl_width_default = 240


    def update(self):
        messages = self.runtime.messages
        messages.clear()
        nlv = NodeLayoutValidator(self)

        if not nlv.assert_image_colorspace(SocketName.BaseColor, ColorSpace.NON_COLOR):
            messages.append(f"- {SocketName.BaseColor.value}:")
            messages.append(f"{ColorSpace.NON_COLOR.value} Expected")
        

    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):

        ngb.create_color_input(SocketName.BaseColor)
        ngb.create_float_input(SocketName.Metallic, default_value=0.0)
        ngb.create_float_input(SocketName.Roughness, default_value=0.5)
        ngb.create_float_input(SocketName.Alpha)
        ngb.create_vector_input(SocketName.Normal, True)
        ngb.create_float_input(SocketName.AmbientOcclusion, True)

        ngb.create_shader_output(SocketName.BSDF)
        ngb.create_float_output(SocketName.Alpha)

        ngb.create_panel("Advanced")
        ngb.create_color_input(SocketName.Emissive, default_value=(0,0,0,1))
        ngb.create_float_input(SocketName.ClearCoat, default_value=0)
        ngb.create_float_input(SocketName.ClearCoatRoughness, default_value=1)

        inputs, outputs = ngb.create_io()
        principled = ngb.create_node(NodeName.BsdfPrincipled)
        principled.inputs[SocketName.EmissionStrength].default_value = 1.0
        ao_scale = ngb.create_node(NodeName.VectorMath, [None, (0.5,0.5,0.5), (0.5,0.5,0.5)], operation=Operation.MULTIPLY_ADD)
        ao_mix = ngb.create_node(NodeName.VectorMath, operation=Operation.MULTIPLY)

        ngb.link(inputs, SocketName.AmbientOcclusion, ao_scale, 0)
        ngb.link(inputs, SocketName.BaseColor, ao_mix, 0)
        ngb.link(ao_scale, 0, ao_mix, 1)
        ngb.link(ao_mix, 0, principled, SocketName.BaseColor)

        ngb.link(inputs, SocketName.Metallic, principled)
        ngb.link(inputs, SocketName.Roughness, principled)
        ngb.link(inputs, SocketName.Normal, principled)
        ngb.link(inputs, SocketName.Normal, principled, SocketName.CoatNormal)
        ngb.link(inputs, SocketName.Emissive, principled, SocketName.EmissionColor)
        ngb.link(inputs, SocketName.ClearCoat, principled, SocketName.CoatWeight)
        ngb.link(inputs, SocketName.ClearCoatRoughness, principled, SocketName.CoatRoughness)

        ngb.link(principled, SocketName.BSDF, outputs)
        ngb.link(inputs, SocketName.Alpha, outputs)
    


class BeamStageMix(BaseShaderNode):

    bl_idname = f"{SHADER_NODE_PREFIX}StageMix"
    bl_label = "BNG Stage Mix 1.5"
    bl_nclass = "SHADER"
    #bl_icon = 'SHADERFX'


    def update(self):
        self.update_alpha_link(0, 1)
        self.update_alpha_link(2, 3)


    def post_init(self):
        pass
        #self.inputs["Base.Alpha"].hide = True
        #self.inputs["Overlay.Alpha"].hide = True


    def create_node_group(ngb: NodeGroupBuilder):

        ngb.create_shader_input("Base")
        ngb.create_float_input("Base.Alpha", True, default_value=1)
        ngb.create_shader_input("Overlay")
        ngb.create_float_input("Overlay.Alpha", True, default_value=0)

        ngb.create_shader_output(SocketName.Shader)
        ngb.create_float_output(SocketName.Alpha)

        inputs, outputs = ngb.create_io()

        mix = ngb.create_node(NodeName.MixShader)

        sub = ngb.create_math(Operation.SUBTRACT, value0=1.0)
        mul = ngb.create_math(Operation.MULTIPLY)
        add = ngb.create_math(Operation.ADD)

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

    bl_idname = f"{SHADER_NODE_PREFIX}Material"
    bl_label = "BNG Material"
    bl_icon = "MATERIAL"
    bl_nclass = "SHADER"
    bl_width_default = 200


    class Sockets(str, Enum):
        CLIP = "Alpha Clip"
        CLIP_T = "Alpha Clip Threshold"
        BLEND = "Alpha Blend"
        DOUBLE_SIDED = "Double Sided"
        INVERT_BACKFACE_NORMALS = "Invert Backface Normals"
        SHADOWS = "Cast Shadows"


    def update(self):
        self.update_alpha_link(0, 1)


    @staticmethod
    def create_node_group(ngb: NodeGroupBuilder):
        
        LS = BeamMaterial.Sockets

        ngb.create_shader_input(SocketName.Shader)
        ngb.create_float_input(SocketName.Alpha, True)

        ngb.create_bool_input(LS.CLIP)
        ngb.create_float_input(LS.CLIP_T, default_value = 0)
        ngb.create_bool_input(LS.BLEND)
        ngb.create_bool_input(LS.DOUBLE_SIDED)
        ngb.create_bool_input(LS.INVERT_BACKFACE_NORMALS, default_value=True)
        ngb.create_bool_input(LS.SHADOWS, default_value=True)
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

        ngb.link(transparent, 0, mix_blend, 1)
        ngb.link(transparent, 0, mix_clip, 1)
        ngb.link(inputs, SocketName.Shader, mix_blend, 2)
        ngb.link(mix_blend, 0, mix_clip, 2)
        ngb.link(mix_clip, 0, outputs, 0)

        ngb.link(inputs, SocketName.Alpha, blend_enabled, 0)
        ngb.link_bool(inputs, LS.BLEND, blend_enabled, 1, True)
        ngb.link(blend_enabled, 0, mix_blend, 0)

        ngb.link(inputs, SocketName.Alpha, clip_t, 0)
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
        "Material",
        BeamBDSF10Basic,
        BeamBSDF15,
        BeamStageMix, 
        BeamMaterial, 
        None,
        "Factor", 
        BeamFactorColor, 
        BeamFactorFloat, 
        None,
        "Detail",
        BeamDetailUVScale, 
        BeamDetailColor, 
        BeamDetailNormal,
        None,
        "Utils",
        BeamBSDFCollision,
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
    def addmenu_append(self, context):
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
        BeamDetailColor, 
        BeamDetailNormal,
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