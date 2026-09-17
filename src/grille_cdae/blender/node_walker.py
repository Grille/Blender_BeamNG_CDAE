from grille_cdae.common import *
from grille_cdae.enums import *



type _InputKey = SocketAccessor | bpy.types.NodeSocket



def _get_link0(socket: types.NodeSocket | None):
    if socket is None: return None
    if not socket.is_linked: return None
    assert socket.links is not None
    return socket.links[0]


def _find_node[T:types.Node](tree: types.ShaderNodeTree | None, btype: type[T]):
    if tree is None: return None

    for node in tree.nodes:
        if isinstance(node, btype):
            return node

    return None



class NodeLayoutError(Exception):

    def __init__(self, *args):
        super().__init__(*args)



class NodeWalker():

    def __init__(self, node: bpy.types.Node | None = None, stack: list[types.ShaderNodeGroup] | None = None):
        self.current = node
        self.group_stack = [] if stack is None else list(stack)
        self.skip_groups = True
        self.raise_layout_errors = True
        self.last_socket_name: str = ""
        self.last_socket_value: SocketValue | None = None


    def _raise_layout_error(self, msg: str):
        if self.raise_layout_errors: raise NodeLayoutError(msg)
        return None


    def is_node_idname(self, ntype: str | type[types.Node]):
        assert self.current is not None
        return butils.get_idname(self.current) == butils.get_idname(ntype)
    

    def is_node_any_idname(self, *ntypes: str | type[types.Node]):
        for ntype in ntypes:
            if self.is_node_idname(ntype): return True
        return False


    def find_material_output(self, nodes: bpy.types.Nodes):
        for node in nodes:
            if node.bl_idname == NodeName.OutputMaterial and cast(bpy.types.ShaderNodeOutputMaterial, node).is_active_output:
                self.current = node
                break
        return self.current is not None


    def get_input(self, input_key: _InputKey, throw: bool = True) -> bpy.types.NodeSocket | None:

        if isinstance(input_key, bpy.types.NodeSocket):
            return input_key

        assert self.current is not None
        
        if isinstance(input_key, str):
            get = self.current.inputs.get
            return get(input_key) if throw else get(input_key, None)
        
        elif isinstance(input_key, int):
            if input_key < len(self.current.inputs): return self.current.inputs[input_key]
            elif throw:  raise ValueError(f"{input_key} out of range.")
            else: return None

        raise TypeError(input_key)


    def has_input(self, input_key: _InputKey):
        return self.get_input(input_key, False) is not None
        
        
    def get_node(self, input_key: _InputKey, throw = True) -> bpy.types.Node | None:
        
        input = self.get_input(input_key, throw=throw)
        link0 = _get_link0(input)
        if link0 is None: return None
        return self.walk_link_recursively(link0)


    def walk_link_recursively(self, link: bpy.types.NodeLink) -> bpy.types.Node | None:

        assert link.from_node is not None
        assert link.from_socket is not None

        from_node = link.from_node
        from_socket = link.from_socket
        def from_socket_index(): return list(from_node.outputs).index(from_socket)

        self.last_socket_name = from_socket.name
        self.last_socket_value = None

        if self.skip_groups:

            if isinstance(from_node, types.ShaderNodeGroup):

                group_output_node = _find_node(from_node.node_tree, types.NodeGroupOutput)
                if group_output_node is None: return None

                inner_output_input = group_output_node.inputs[from_socket_index()]
                link0 = _get_link0(inner_output_input)
                if link0 is None: return None
                self.group_stack.append(from_node)
                return self.walk_link_recursively(link0)

            elif isinstance(from_node, types.NodeGroupInput):

                if len(self.group_stack) == 0:
                    return self._raise_layout_error("Group input found, but stack is empty.")
                
                outer_node = self.group_stack.pop()
                outer_input = outer_node.inputs[from_socket_index()]
                link0 = _get_link0(outer_input)

                if link0 is None:
                    self.last_socket_value = butils.get_default_value(outer_input)
                    return None

                return self.walk_link_recursively(link0)

        return from_node
    

    def try_follow(self, input_key: _InputKey):
        self.current = self.get_node(input_key, False)
        return self.current is not None
    

    def follow(self, input_key: _InputKey):
        if not self.try_follow(input_key):
            raise NodeLayoutError(f"Next node on {input_key} is None.")
        

    def fork(self, input_key: _InputKey | None = None):
        walk = type(self)(self.current, stack=self.group_stack)
        if (input_key is not None):
            walk.follow(input_key)
        return walk
    

    def _get_any_value(self, input_key: _InputKey):
        input = self.get_input(input_key, throw = False)
        if input is None:
            return None
        stack = list(self.group_stack) if input.is_linked else self.group_stack
        try:
            node = self.get_node(input, throw=False)
            if node is None:
                if self.last_socket_value is not None:
                    return self.last_socket_value
                return butils.get_default_value(input)
            return butils.get_default_value(node.outputs[0])
        finally:
            self.group_stack = stack


    def get_cast_value[T](self, input_key: _InputKey, cast: Callable[[Any], T]):
        try:
            return cast(self._get_any_value(input_key))
        except: 
            return None


    def get_float_value(self, input_key: _InputKey):
        return self.get_cast_value(input_key, float)
        

    def get_bool_value(self, input_key: _InputKey):
        return self.get_cast_value(input_key, bool)
    

    def get_color_value(self, input_key: _InputKey):
        return self.get_cast_value(input_key, Color4F.from_obj)
        

    def get_vector_value(self, input_key: _InputKey):
        return self.get_cast_value(input_key, Vec3F.from_obj)
        

    def is_linked(self, input_key: _InputKey) -> bool:
        input = self.get_input(input_key)
        if input is None:
            return False
        return input.is_linked
            

    def get_image(self) -> types.Image | None:
        obj = getattr(self.current, "image", None)
        if obj is None: return None
        if isinstance(obj, types.Image): return obj
        raise Exception(f"{type(self.current)} is not a valid image node.")
    

    def get_default_value(self, input_key: _InputKey):
        input = self.get_input(input_key)
        if input is None: return None
        return butils.get_default_value(input)