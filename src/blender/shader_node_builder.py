import bpy
from dataclasses import dataclass, asdict

from typing import NamedTuple
from .enums import *
from .node_walker import NodeWalker
from .enums import *



class NodeTreeBuilder:

    @dataclass
    class NodeSocket:
        node: bpy.types.ShaderNode
        accessor: str | int = 0



    class Signature:

        class IO(NamedTuple):
            inputs: 'NodeTreeBuilder.Signature'
            outputs: 'NodeTreeBuilder.Signature'


        @dataclass
        class Socket:
            name: str
            type: SocketType


        def __init__(self, *sockets: 'Socket'):
            self.sockets = sockets
    

        def apply_to_collection(self, collection: bpy.types.NodeCombineBundleItems):
            for socket in self.sockets:
                item = collection.new(socket.type.to_data_type(), socket.name)
                if item.name != socket.name: raise Exception(f"Invalid Socket Name '{socket.name}' converted to '{item.name}'")



    
    def __init__(self, tree: bpy.types.ShaderNodeTree):
        self.tree = tree
        self.interface = self.tree.interface


    def create_node(self, type: NodeName, default_values: list = None, **dict) -> bpy.types.ShaderNode:
        node = self.tree.nodes.new(type)
        for key, value in dict.items():
            setattr(node, key, value)
        if default_values is not None:
            for idx, value in enumerate(default_values):
                if value is not None:
                    node.inputs[idx].default_value = value
        return node
    

    def clear(self):
        self.tree.nodes.clear()


    def create_bundle_node(self, type: NodeName, signature: 'Signature'):
        node: bpy.types.NodeCombineBundle | bpy.types.NodeSeparateBundle = self.create_node(type)
        node.define_signature = True
        signature.apply_to_collection(node.bundle_items)
        return node


    class Closure(NamedTuple):
        input: bpy.types.NodeClosureInput
        output: bpy.types.NodeClosureOutput


    def create_closure(self, signatures: 'Signature.IO'):
        input: bpy.types.NodeClosureInput = self.create_node(NodeName.ClosureInput)
        output: bpy.types.NodeClosureOutput = self.create_node(NodeName.ClosureOutput)
        input.pair_with_output(output)
        output.define_signature = True
        signatures.inputs.apply_to_collection(output.input_items)
        signatures.outputs.apply_to_collection(output.output_items)
        return NodeTreeBuilder.Closure(input, output)


    def create_closure_eval(self, signatures: 'Signature.IO'):
        node: bpy.types.NodeEvaluateClosure = self.create_node(NodeName.EvaluateClosure)
        node.define_signature = True
        signatures.inputs.apply_to_collection(node.input_items)
        signatures.outputs.apply_to_collection(node.output_items)
        return node


    def combine_bundle(self, signature: 'Signature', output: 'NodeSocket | None' = None, *input_sockets: 'NodeSocket'):
        node: bpy.types.NodeCombineBundle = self.create_bundle_node(NodeName.CombineBundle, signature)
        for index, socket in enumerate(input_sockets): self.link(socket.node, socket.accessor, node, index)
        if output is not None: self.link(node, 0, output.node, output.accessor)
        return node
    

    def seperate_bundle(self, signature: 'Signature', input: 'NodeSocket | None' = None, *output_sockets: 'NodeSocket'):
        node: bpy.types.NodeSeparateBundle = self.create_bundle_node(NodeName.SeparateBundle, signature)
        for index, socket in enumerate(output_sockets): self.link(node, index, socket.node, socket.accessor)
        if input is not None: self.link(input.node, input.accessor, node, 0)
        return node
    
    
    def create_math(self, operation: Operation, value0: float = None, value1: float = None, value2: float = None):
        default_values = [value0, value1, value2]
        node: bpy.types.ShaderNodeMath = self.create_node(NodeName.Math, default_values, operation=operation)
        return node
    

    def create_teximage(self, image: str | bpy.types.Image | None, color_space: ColorSpace | None = None) -> bpy.types.TextureNode:
        node: bpy.types.ShaderNodeTexImage = self.create_node(NodeName.TexImage)

        if isinstance(image, bpy.types.Image):
            node.image = image
        elif isinstance(image, str):
            if image in bpy.data.images:
                node.image = bpy.data.images[image]
            else:
                node.image = bpy.data.images.load(image)

        if node.image and color_space is not None:
            node.image.colorspace_settings.name = color_space

        return node
    

    def link(self, node0: bpy.types.ShaderNode, socket0: str | int, node1: bpy.types.ShaderNode, socket1: str | int = None): 
        if socket1 is None: socket1 = socket0

        try:
            out_socket = node0.outputs[socket0]
            in_socket = node1.inputs[socket1]
        except (KeyError, IndexError, AttributeError) as e:
            raise ValueError(f"Invalid socket index or name: {e}")

        if not out_socket.is_output or in_socket.is_output:
            raise ValueError("Sockets are not output/input as expected.")
        
        self.tree.links.new(node0.outputs[socket0], node1.inputs[socket1])


    def link_bool(self, node0: bpy.types.ShaderNode, socket0: str | int, node1: bpy.types.ShaderNode, socket1: str | int = None, invert = False):
        op = Operation.LESS_THAN if invert else Operation.GREATER_THAN
        math = self.create_math(op, value1=0.5)
        self.link(node0, socket0, math, 0)
        self.link(math, 0, node1, socket1)


    def arrange_nodes(self, x_spacing=250, y_spacing=150):
        nodes = list(self.tree.nodes)

        # Find depth of each node by walking backwards through inputs
        depths: dict[bpy.types.Node, int] = {}

        def get_depth(node: bpy.types.Node):
            if node in depths:
                return depths[node]

            depth = 0
            for inp in node.inputs:
                if inp.is_linked:
                    for link in inp.links:
                        depth = max(depth, get_depth(link.from_node) + 1)

            depths[node] = depth
            return depth

        for node in nodes:
            get_depth(node)

        # Group nodes by depth
        levels: dict[int, list[bpy.types.Node]] = {}
        for node, depth in depths.items():
            levels.setdefault(depth, []).append(node)

        # Place nodes
        for depth, level_nodes in levels.items():
            for index, node in enumerate(level_nodes):
                node.location.x = depth * x_spacing
                node.location.y = -index * y_spacing

        return levels



class NodeGroupBuilder(NodeTreeBuilder):

    def __init__(self, idname: str):
        tree = bpy.data.node_groups.new(idname, NodeName.ShaderNodeTree)
        super().__init__(tree)
        self.panel = None
        self.panel_position = 0


    def create_io(self):
        inputs = self.create_node(NodeName.GroupInput)
        outputs = self.create_node(NodeName.GroupOutput)
        return (inputs, outputs)


    def create_panel(self, name: str, description='', default_closed=True):
        self.panel = self.interface.new_panel(name, description=description, default_closed=default_closed)
        self.panel_position = 0


    def move_to_panel(self, item: bpy.types.NodeTreeInterfaceItem):
        if self.panel is None: return
        self.interface.move_to_parent(item, self.panel, self.panel_position)
        self.panel_position += 1


    def create_any_input(self, name: str, type: SocketType, hide_value: bool = False, default_value = None, subtype: str = None):
        input: bpy.types.NodeSocket = self.interface.new_socket(name, in_out=SocketIOType.INPUT, socket_type=f"NodeSocket{type.value}")

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
    

    def create_vector_input(self, name: str, hide_value = False, default_value: float = (0.0,0.0,0.0), subtype: str = None, dimensions: int = 3):
        input: bpy.types.NodeSocketVector = self.create_any_input(name, SocketType.Vector, hide_value, default_value, subtype)
        if hasattr(input, "dimensions"): input.dimensions = dimensions
        return input
    

    def create_color_input(self, name: str, hide_value = False, default_value = (1.0,1.0,1.0,1.0)):
        input = self.create_any_input(name, SocketType.Color, hide_value, default_value)
        return input
    

    def create_shader_input(self, name: str):
        return self.create_any_input(name, SocketType.Shader)
    

    def create_bundle_input(self, name: str) -> bpy.types.NodeSocketBundle:
        return self.create_any_input(name, SocketType.Bundle)


    def create_closure_input(self, name: str) -> bpy.types.NodeSocketClosure:
        return self.create_any_input(name, SocketType.Closure)
    

    def create_any_output(self, name: str, type: SocketType):
        output = self.interface.new_socket(name, in_out=SocketIOType.OUTPUT, socket_type=f"NodeSocket{type.value}")
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
    

    def create_bundle_output(self, name: str):
        return self.create_any_output(name, SocketType.Bundle)


    def create_closure_output(self, name: str):
        return self.create_any_output(name, SocketType.Closure)