import bpy

from dataclasses import dataclass

from .numerics import *
from .blender_enums import *

class NodeLayoutError(Exception):

    def __init__(self, *args):
        super().__init__(*args)


class NodeWalker():

    def __init__(self, node: bpy.types.Node = None, stack: list = None):
        self.current = node
        self.group_stack = [] if stack is None else list(stack)
        self.skip_groups = True
        self.last_socket_name: str = ""
        self.last_socket_index: int = 0


    def is_node_idname(self, ntype: str | bpy.types.Node):
        current = self.current.bl_idname
        if isinstance(ntype, str):
            return current == ntype
        elif hasattr(ntype, "bl_idname"):
            return current == ntype.bl_idname
        raise TypeError()
    

    def find_material_output(self, nodes: bpy.types.Nodes):
        for node in nodes:
            if node.bl_idname == NodeName.OutputMaterial and node.is_active_output:
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

        self.last_socket_name = from_socket.name
        self.last_socket_index = from_socket_index

        if self.skip_groups:

            if from_node.bl_idname == NodeName.Group:
                for node in from_node.node_tree.nodes:
                    if node.bl_idname == NodeName.GroupOutput:
                        group_output_node = node
                        break

                if group_output_node is None:
                    return None

                inner_output_input = group_output_node.inputs[from_socket_index()]
                if not inner_output_input.is_linked:
                    return None
                
                self.group_stack.append(from_node)
                return self.walk_link_recursively(inner_output_input.links[0])

            elif from_node.bl_idname == NodeName.GroupInput:

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
        

    def fork(self, input_key: str | int = None):
        walk = type(self)(self.current, stack=self.group_stack)
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
            value = self._get_any_value(input_key, NodeName.Value)
            return float(value)
        except:
            return None
    

    def get_color_value(self, input_key: str | int) -> Color4F | None:
        try:
            value = self._get_any_value(input_key, NodeName.RGB)
            return Color4F.from_list4(value)
        except:
            return None
            

    def get_image(self) -> bpy.types.Image:
        return self.current.image
    

    def get_default_value(self, input_key: str | int):
        input = self.get_input(input_key)
        return input.default_value