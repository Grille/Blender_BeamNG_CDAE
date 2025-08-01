import bpy

from dataclasses import dataclass

from .numerics import *
from .blender_shader_nodes import *


class NodeLayoutError(Exception):

    def __init__(self, *args):
        super().__init__(*args)


class NodeWalker():

    @dataclass
    class Socket:
        image: bpy.types.Image = None
        layer: str = None
        color: Color4F = None
        factor: float = None
        strength: float = None
        scale: Vec2F = None
        child: 'NodeWalker.Socket' = None
        issues: list[str] = None

        def set_value_or_color(self, value: float | tuple):
            if isinstance(value, float):
                self.factor = value
            else:
                self.color = Color4F.from_list(value)


    @dataclass
    class MaterialSettings:
        alpha_clip: bool = False
        alpha_clip_threshold: int = 0
        alpha_blend: bool = False
        double_sided: bool = False
        invert_backface_normals: bool = False
        cast_shadows: bool = True

    
    @dataclass
    class StageHead:
        context: 'NodeWalker'

    
    def __init__(self, node: bpy.types.Node = None):
        self.current = node
        self.group_stack = []


    def is_node_idname(self, idname: str):
        return self.current.bl_idname == idname
    

    def find_output(self, nodes: bpy.types.Nodes):
        for node in nodes:
            if node.bl_idname == NodeNames.OutputMaterial and node.is_active_output:
                self.current = node
                break
        return self.current is not None


    def get_input(self, input_key: str | int, throw: bool = True) -> bpy.types.NodeSocket | None:

        if isinstance(input_key, str):
            return self.current.inputs.get(input_key) 
        
        elif isinstance(input_key, int):
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

            group_output = from_node.outputs[from_socket_index()]
            if not group_output.is_linked:
                return None
            
            self.group_stack.append(from_node)
            return self.walk_link_recursively(group_output.links[0])

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
        node = self.get_node(input_key)
        if node is not None:
            self.current = node
            return True
        return False
    

    def follow(self, input_key: str | int):
        print(f"follow {input_key}")

        if not self.try_follow(input_key):
            raise Exception()
        

    def fork(self, input_key: str | int = None) -> 'NodeWalker':
        walk = NodeWalker(self.current)
        if (input_key is not None):
            walk.follow(input_key)
        return walk
    

    def _get_any_value(self, input_key: str | int) -> any:
        node = self.get_node(input_key, throw=False)
        if node is not None and node.bl_idname:
            return node.outputs[0].default_value
        input = self.get_input(input_key, throw=True)
        return input.default_value
    

    def get_float_value(self, input_key: str | int) -> float:
        try:
            value = self._get_any_value(input_key)
            return float(value)
        except:
            return 0
    

    def get_color_value(self, input_key: str | int) -> Color4F:
        try:
            value = self._get_any_value(input_key)
            return Color4F.from_list(value)
        except:
            return Color4F(1,1,1,1)


    def parse_socket_tree(self, socket: 'NodeWalker.Socket'):

        if self.is_node_idname(BeamDetailColor.bl_idname):
            child = NodeWalker.Socket(issues=[])
            child.strength = self.get_float_value("Strength")
            self.get_socket("Detail", child)
            socket.child = child
            socket.color = self.get_color_value("Base")
            self.follow("Base")

        if self.is_node_idname(BeamDetailNormal.bl_idname):
            child = NodeWalker.Socket(issues=[])
            self.get_socket("Detail", child)
            socket.child = child
            self.follow("Base")


        if self.is_node_idname(BeamFactorFloat.bl_idname):
            socket.factor = self.get_float_value("Factor")
            self.follow("Texture Map")

        if self.is_node_idname(BeamFactorColor.bl_idname):
            print("GET color factor")
            socket.color = self.get_color_value("Factor")
            print(socket.color)
            self.follow("Texture Map")


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


    def get_socket(self, input_key: str | int, socket: 'NodeWalker.Socket' = None) -> 'NodeWalker.Socket':

        if socket is None:
            socket = NodeWalker.Socket(issues=[])

        try:
            socket.color = self.get_color_value(input_key)
            socket.factor = self.get_float_value(input_key)
            ctx = self.fork()
            if ctx.try_follow(input_key):
                ctx.parse_socket_tree(socket)

        finally:
            return socket


    def parse_stage_recursively(self, stages: list['NodeWalker.StageHead'] = None):

        if stages is None:
            stages = []

        if self.is_node_idname(BeamStageMix.bl_idname):
            context = self.fork("Overlay")
            self.follow("Base")
            self.parse_stage_recursively(stages)
            stages.append(NodeWalker.StageHead(context))
        else:
            stages.append(NodeWalker.StageHead(self))

        return stages
    

    def parse_mat_settings(self) -> 'NodeWalker.MaterialSettings':
        mat = NodeWalker.MaterialSettings()
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