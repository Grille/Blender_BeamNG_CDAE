import bpy

from dataclasses import dataclass

from .numerics import *
from .blender_shader_nodes import *


class NodeLayoutError(Exception):

    def __init__(self, *args):
        super().__init__(*args)


class NodeWalker():

    @dataclass
    class MatSocket:
        exists: bool = False
        image: bpy.types.Image = None
        layer: str = None
        color: Color4F = None
        factor: float = None
        strength: float = None
        scale: Vec2F = None
        child: 'NodeWalker.MatSocket' = None
        issues: list[str] = None

        def set_value_or_color(self, value: float | tuple):
            if isinstance(value, float):
                self.factor = value
            else:
                self.color = Color4F.from_list4(value)


    @dataclass
    class MatSettings:
        alpha_clip: bool = False
        alpha_clip_threshold: int = 0
        alpha_blend: bool = False
        double_sided: bool = False
        invert_backface_normals: bool = False
        cast_shadows: bool = True

    
    @dataclass
    class MatStage:
        context: 'NodeWalker'


    def __init__(self, node: bpy.types.Node = None, stack: list = None):
        self.current = node
        self.group_stack = [] if stack is None else list(stack)


    def is_node_idname(self, idname: str):
        return self.current.bl_idname == idname
    

    def find_material_output(self, nodes: bpy.types.Nodes):
        for node in nodes:
            if node.bl_idname == NodeNames.OutputMaterial and node.is_active_output:
                self.current = node
                break
        return self.current is not None


    def get_input(self, input_key: str | int, throw: bool = True) -> bpy.types.NodeSocket | None:

        if isinstance(input_key, bpy.types.NodeSocket):
            return input_key
        
        if isinstance(input_key, str):
            return self.current.inputs.get(input_key) 
        
        elif isinstance(input_key, int) and input_key < len(self.current.inputs):
            return self.current.inputs[input_key]
        
        elif throw:
            raise NodeLayoutError(f"Expected input {input_key} not found.")
        
        return None
        
        
    def get_node(self, input_key: str | int, throw = True) -> bpy.types.Node | None:
        
        input = self.get_input(input_key, throw=throw)

        if not input or not input.is_linked:
            return None
        
        return self.walk_link_recursively(input.links[0])


    def walk_link_recursively(self, link) -> bpy.types.Node | None:

        from_node: bpy.types.Node = link.from_node
        from_socket: bpy.types.NodeSocket = link.from_socket
        from_socket_index = lambda : list(from_node.outputs).index(from_socket)

        if from_node.bl_idname == NodeNames.Group:

            print("Hit group")

            print(len(from_node.node_tree.nodes))
            for node in from_node.node_tree.nodes:
                if node.bl_idname == NodeNames.GroupOutput:
                    
                    print("found node")
                    group_output_node = node
                    break

            if group_output_node is None:
                return None

            inner_output_input = group_output_node.inputs[from_socket_index()]
            if not inner_output_input.is_linked:
                return None
            
            print("found input")
            
            self.group_stack.append(from_node)
            return self.walk_link_recursively(inner_output_input.links[0])

        elif from_node.bl_idname == NodeNames.GroupInput:

            if len(self.group_stack) == 0:
                raise NodeLayoutError("Group input found, but stack is empty.")
            
            outer_node = self.group_stack.pop()
            outer_input = outer_node.inputs[from_socket_index()]

            if not outer_input.is_linked:
                return None
            
            return self.walk_link_recursively(outer_input.links[0])

        return from_node
    

    def try_follow(self, input_key: str | int):
        self.current = self.get_node(input_key, False)
        return self.current is not None
    

    def follow(self, input_key: str | int):
        if not self.try_follow(input_key):
            raise NodeLayoutError(f"Next node on {input_key} is None.")
        

    def fork(self, input_key: str | int = None) -> 'NodeWalker':
        walk = NodeWalker(self.current, stack=self.group_stack)
        if (input_key is not None):
            walk.follow(input_key)
        return walk
    

    def _get_any_value(self, input_key: str | int, idname):
        input = self.get_input(input_key, throw = False)
        if input is None:
            return None
        stack = list(self.group_stack) if input.is_linked else self.group_stack
        try:
            node = self.get_node(input, throw=False)
            if node is None:
                return input.default_value
            elif node.bl_idname == idname:
                return node.outputs[0].default_value
            return None
        finally:
            self.group_stack = stack

    

    def get_float_value(self, input_key: str | int) -> float | None:
        try:
            value = self._get_any_value(input_key, NodeNames.Value)
            return float(value)
        except:
            return None
    

    def get_color_value(self, input_key: str | int) -> Color4F | None:
        try:
            value = self._get_any_value(input_key, NodeNames.RGB)
            return Color4F.from_list4(value)
        except:
            return None


    def parse_socket_tree(self, socket: 'NodeWalker.MatSocket'):

        if self.is_node_idname(BeamDetailColor.bl_idname):
            child = NodeWalker.MatSocket(issues=[])
            child.strength = self.get_float_value("Strength")
            self.get_socket("Detail", child)
            socket.child = child
            socket.color = self.get_color_value("Base")
            self.follow("Base")

        if self.is_node_idname(BeamDetailNormal.bl_idname):
            child = NodeWalker.MatSocket(issues=[])
            self.get_socket("Detail", child)
            socket.child = child
            self.follow("Base")


        if self.is_node_idname(BeamFactorFloat.bl_idname):
            socket.factor = self.get_float_value("Factor")
            self.follow("Texture Map")

        if self.is_node_idname(BeamFactorColor.bl_idname):
            socket.color = self.get_color_value("Factor")
            self.follow("Texture Map")

        if self.is_node_idname(NodeNames.Mix):
            socket.color = self.get_color_value(7)
            self.follow(6)

        if self.is_node_idname(NodeNames.VectorMath):
            socket.color = self.get_color_value(1)
            self.follow(0)

        if self.is_node_idname(NodeNames.Math):
            socket.factor = self.get_float_value(1)
            self.follow(0)

        if self.is_node_idname(NodeNames.NormalMap):
            socket.strength = self.get_float_value("Strength")
            self.follow("Color")


        if self.is_node_idname(NodeNames.TexImage):
            socket.image = self.get_image()
            if not self.try_follow("Vector"): return


        if self.is_node_idname(BeamDetailUVScale.bl_idname):
            u = self.get_float_value("Scale U")
            v = self.get_float_value("Scale V")
            socket.scale = Vec2F(u, v)
            self.follow("UV")

        if self.is_node_idname(NodeNames.VectorMath):
            scale = self.get_default_value(1)
            socket.scale = Vec2F(scale[0], scale[1])
            self.follow(0)


        if self.is_node_idname(NodeNames.UVMap):
            socket.layer = self.current.uv_map


    def get_socket(self, input_key: str | int, socket: 'NodeWalker.MatSocket' = None) -> 'NodeWalker.MatSocket':

        if socket is None:
            socket = NodeWalker.MatSocket(issues=[])

        try:
            socket.color = self.get_color_value(input_key)
            socket.factor = self.get_float_value(input_key)
            socket.exists = True
            ctx = self.fork()
            if ctx.try_follow(input_key):
                ctx.parse_socket_tree(socket)

        except Exception as e:
            print(e)

        finally:
            return socket


    def parse_stage_recursively(self, stages: list['NodeWalker.MatStage'] = None):

        if stages is None:
            stages = []

        if self.is_node_idname(BeamStageMix.bl_idname):
            context = self.fork("Overlay")
            self.follow("Base")
            self.parse_stage_recursively(stages)
            stages.append(NodeWalker.MatStage(context))
        else:
            stages.append(NodeWalker.MatStage(self))

        return stages
    

    def parse_mat_settings(self) -> 'NodeWalker.MatSettings':
        mat = NodeWalker.MatSettings()
        if self.is_node_idname(BeamMaterial.bl_idname):
            mat.alpha_clip = self.get_float_value(BeamMaterial.Sockets.CLIP) > 0.5
            mat.alpha_clip_threshold = self.get_float_value(BeamMaterial.Sockets.CLIP_T)
            mat.alpha_blend = self.get_float_value(BeamMaterial.Sockets.BLEND) > 0.5
            mat.double_sided = self.get_float_value(BeamMaterial.Sockets.DS) > 0.5
            mat.invert_backface_normals = self.get_float_value(BeamMaterial.Sockets.IBN) > 0.5
            mat.cast_shadows = self.get_float_value(BeamMaterial.Sockets.SHADOWS) > 0.5
            self.try_follow(Sockets.Shader)
        return mat
            

    def get_image(self) -> bpy.types.Image:
        return self.current.image
    

    def get_default_value(self, input_key: str | int):
        input = self.get_input(input_key)
        return input.default_value