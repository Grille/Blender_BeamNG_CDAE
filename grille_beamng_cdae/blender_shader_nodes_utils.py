import bpy
from .blender_enums import *


class NodeGroupBuilder():

    def __init__(self, idname: str):
        self.ng: bpy.types.ShaderNodeTree = bpy.data.node_groups.new(idname, NodeName.ShaderNodeTree)
        self.interface: bpy.types.NodeTreeInterface = self.ng.interface
        self.panel = None
        self.panel_position = 0


    def create_panel(self, name: str, description='', default_closed=True):
        self.panel = self.interface.new_panel(name, description=description, default_closed=default_closed)
        self.panel_position = 0


    def move_to_panel(self, item):
        if self.panel is None: return
        self.interface.move_to_parent(item, self.panel, self.panel_position)
        self.panel_position += 1


    def create_any_input(self, name: str, type: SocketType, hide_value: bool = False, default_value = None, subtype: str = None):
        input: bpy.types.NodeSocket = self.interface.new_socket(name, in_out=SocketType.INPUT, socket_type=f"NodeSocket{type.value}")

        input.hide_value = hide_value
        if default_value is not None:
            input.default_value = default_value
        if subtype is not None:
            input.subtype = subtype

        self.move_to_panel(input)

        return input
    

    def create_bool_input(self, name: str, hide_value = False, default_value = False):
        input = self.create_any_input(name, SocketType.Bool, hide_value, default_value)
        return input
    

    def create_float_input(self, name: str, hide_value = False, default_value: float = 1.0, subtype = "FACTOR", range: tuple[float,float] = (0.0, 1.0)):
        input: bpy.types.NodeSocketFloat = self.create_any_input(name, SocketType.Float, hide_value, default_value, subtype)
        if range is not None:
            input.min_value = range[0]
            input.max_value = range[1]
        return input
    

    def create_vector_input(self, name: str, hide_value = False, subtype: str = None):
        input = self.create_any_input(name, SocketType.Vector, hide_value, subtype=subtype)
        return input
    

    def create_color_input(self, name: str, hide_value = False, default_value = (1.0,1.0,1.0,1.0)):
        input = self.create_any_input(name, SocketType.Color, hide_value, default_value)
        return input
    

    def create_shader_input(self, name: str, hide_value = False):
        input = self.create_any_input(name, SocketType.Shader, hide_value)
        return input
    

    def create_any_output(self, name: str, type: SocketType):
        output = self.interface.new_socket(name, in_out=SocketType.OUTPUT, socket_type=f"NodeSocket{type.value}")
        self.move_to_panel(output)
        return output
    

    def create_float_output(self, name: str):
        return self.create_any_output(name, SocketType.Float)
    

    def create_vector_output(self, name: str):
        return self.create_any_output(name, SocketType.Vector)
    

    def create_color_output(self, name: str):
        return self.create_any_output(name, SocketType.Color)
    

    def create_shader_output(self, name: str):
        return self.create_any_output(name, SocketType.Shader)
    

    def create_node(self, type: NodeName, default_values: list = None, **dict) -> bpy.types.ShaderNode:
        node = self.ng.nodes.new(type)
        for key, value in dict.items():
            setattr(node, key, value)
        if default_values is not None:
            for idx, value in enumerate(default_values):
                if value is not None:
                    node.inputs[idx].default_value = value
        return node
    

    def create_math(self, operation: Operation, value0: float = None, value1: float = None):
        default_values = [value0, value1]
        node: bpy.types.ShaderNodeMath = self.create_node(NodeName.Math, default_values, operation=operation)
        return node
    

    def create_io(self):
        inputs = self.create_node(NodeName.GroupInput)
        outputs = self.create_node(NodeName.GroupOutput)
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
        
        self.ng.links.new(node0.outputs[socket0], node1.inputs[socket1])


    def link_bool(self, node0: bpy.types.ShaderNode, socket0: str | int, node1: bpy.types.ShaderNode, socket1: str | int = None, invert = False):
        op = Operation.LESS_THAN if invert else Operation.GREATER_THAN
        math = self.create_math(op, value1=0.5)
        self.link(node0, socket0, math, 0)
        self.link(math, 0, node1, socket1)